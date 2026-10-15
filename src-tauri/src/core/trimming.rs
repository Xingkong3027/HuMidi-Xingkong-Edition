//! Crop notes, MIDI pedal state and musical metadata on one shared timeline.
use std::io;

use super::{config::PlaybackConfig, midi::TempoMap, models::Note};

pub fn apply_trim(
    mut notes: Vec<Note>,
    tempo_map: TempoMap,
    midi_pedal: Vec<(f64, bool)>,
    config: &PlaybackConfig,
) -> io::Result<(Vec<Note>, TempoMap, Vec<(f64, bool)>)> {
    notes.sort_by(|a, b| a.start_time.total_cmp(&b.start_time));
    if !config.trim_enabled || notes.is_empty() {
        return Ok((notes, tempo_map, midi_pedal));
    }
    let last_end = notes.iter().map(Note::end_time).fold(0.0, f64::max);
    let (start, end) = if config.trim_auto {
        (notes[0].start_time.max(0.0), last_end)
    } else {
        let raw_end = config.trim_end_seconds;
        (
            config.trim_start_seconds.max(0.0),
            if raw_end == 0.0 {
                last_end
            } else {
                raw_end.min(last_end)
            },
        )
    };
    if !start.is_finite() || !end.is_finite() || end <= start {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "裁剪结束时间必须大于开始时间，且均为有效秒数。",
        ));
    }
    let notes: Vec<Note> = notes
        .into_iter()
        .filter_map(|mut note| {
            let clipped_start = note.start_time.max(start);
            let clipped_end = note.end_time().min(end);
            if clipped_end <= clipped_start {
                return None;
            }
            note.start_time = clipped_start - start;
            // Preserve the exact crop boundary; key scheduling has its own minimum hold.
            note.duration = clipped_end - clipped_start;
            Some(note)
        })
        .collect();
    if notes.is_empty() {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "裁剪范围内没有可播放音符。",
        ));
    }
    let mut tempos = vec![(0.0, tempo_map.get_tempo_at(start))];
    tempos.extend(
        tempo_map
            .events()
            .iter()
            .filter(|&&(t, _)| t > start && t <= end)
            .map(|&(t, bpm)| (t - start, bpm)),
    );
    let mut signatures = Vec::new();
    if let Some(&(_, n, d)) = tempo_map
        .time_signatures()
        .iter()
        .rev()
        .find(|&&(t, _, _)| t <= start)
    {
        signatures.push((0.0, n, d));
    }
    signatures.extend(
        tempo_map
            .time_signatures()
            .iter()
            .filter(|&&(t, _, _)| t > start && t <= end)
            .map(|&(t, n, d)| (t - start, n, d)),
    );

    let mut source_pedal = midi_pedal;
    source_pedal.sort_by(|a, b| a.0.total_cmp(&b.0));
    let mut pedal = Vec::new();
    let mut down = source_pedal
        .iter()
        .filter(|&&(t, _)| t <= start)
        .last()
        .map(|&(_, down)| down)
        .unwrap_or(false);
    if down {
        pedal.push((0.0, true));
    }
    for (t, next_down) in source_pedal {
        if t > start && t <= end && next_down != down {
            pedal.push((t - start, next_down));
            down = next_down;
        }
    }
    if down {
        pedal.push((end - start, false));
    }
    Ok((notes, TempoMap::new(tempos, signatures), pedal))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn manual_crop_preserves_overlaps_tempo_and_held_pedal() {
        let notes = vec![
            Note::new(0, 60, 80, 1.0, 4.0),
            Note::new(1, 64, 80, 3.0, 3.0),
        ];
        let map = TempoMap::new(
            vec![(0.0, 500_000), (1.0, 400_000), (3.0, 600_000)],
            vec![(0.0, 3, 4), (3.0, 4, 4)],
        );
        let config = PlaybackConfig {
            trim_enabled: true,
            trim_auto: false,
            trim_start_seconds: 2.0,
            trim_end_seconds: 4.0,
            ..Default::default()
        };
        let (notes, map, pedal) =
            apply_trim(notes, map, vec![(0.0, true), (8.0, false)], &config).unwrap();
        assert_eq!((notes[0].start_time, notes[0].duration), (0.0, 2.0));
        assert_eq!((notes[1].start_time, notes[1].duration), (1.0, 1.0));
        assert_eq!(map.events(), &[(0.0, 400_000), (1.0, 600_000)]);
        assert_eq!(map.time_signatures(), &[(0.0, 3, 4), (1.0, 4, 4)]);
        assert_eq!(pedal, vec![(0.0, true), (2.0, false)]);
    }
    #[test]
    fn auto_crop_removes_leading_silence() {
        let config = PlaybackConfig {
            trim_enabled: true,
            ..Default::default()
        };
        let (notes, _, _) = apply_trim(
            vec![Note::new(0, 60, 80, 7.0, 0.5)],
            TempoMap::new(vec![], vec![]),
            vec![],
            &config,
        )
        .unwrap();
        assert_eq!(notes[0].start_time, 0.0);
        assert_eq!(notes[0].duration, 0.5);
    }
    #[test]
    fn empty_or_reversed_manual_range_is_rejected() {
        let config = PlaybackConfig {
            trim_enabled: true,
            trim_auto: false,
            trim_start_seconds: 4.0,
            trim_end_seconds: 2.0,
            ..Default::default()
        };
        assert!(apply_trim(
            vec![Note::new(0, 60, 80, 0.0, 5.0)],
            TempoMap::new(vec![], vec![]),
            vec![],
            &config
        )
        .is_err());
    }
}
