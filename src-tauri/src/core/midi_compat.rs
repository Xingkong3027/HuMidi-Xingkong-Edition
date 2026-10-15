use std::io;

fn invalid(message: &str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message)
}

fn vlq(bytes: &[u8], cursor: &mut usize, end: usize) -> io::Result<usize> {
    let mut value = 0usize;
    for _ in 0..4 {
        if *cursor >= end {
            return Err(invalid("Truncated MIDI variable length value."));
        }
        let byte = bytes[*cursor];
        *cursor += 1;
        value = (value << 7) | (byte & 0x7f) as usize;
        if byte & 0x80 == 0 {
            return Ok(value);
        }
    }
    Err(invalid("MIDI variable length value exceeds four bytes."))
}

/// Validate channel message data before midly masks high bits. Compatibility
/// mode clips only data bytes at known message positions; it never rewrites the
/// file on disk or attempts to invent missing MIDI structure.
pub fn validated_midi_bytes(data: &[u8], clip: bool) -> io::Result<Vec<u8>> {
    if data.len() < 14 || &data[..4] != b"MThd" {
        return Err(invalid("Not a Standard MIDI File (missing MThd header)."));
    }
    let read_length = |p: usize| u32::from_be_bytes(data[p..p + 4].try_into().unwrap()) as usize;
    let header_len = read_length(4);
    if header_len < 6 {
        return Err(invalid("Invalid MIDI header length."));
    }
    let mut bytes = data.to_vec();
    let mut chunk = 8usize
        .checked_add(header_len)
        .ok_or_else(|| invalid("Invalid MIDI length."))?;
    if chunk > data.len() {
        return Err(invalid("Truncated MIDI header."));
    }
    let declared_tracks = u16::from_be_bytes(data[10..12].try_into().unwrap()) as usize;
    let mut complete_tracks = 0usize;
    while chunk < data.len() {
        // Some exporters append zero padding after the complete SMF. It is not
        // another chunk or an out-of-range channel byte. Require every declared
        // track first, so padding cannot hide a missing/truncated track.
        if data[chunk..].iter().all(|&byte| byte == 0) {
            if complete_tracks > 0 && complete_tracks >= declared_tracks {
                break;
            }
            return Err(invalid("Missing MIDI track before trailing padding."));
        }
        if chunk + 8 > data.len() {
            return Err(invalid("Truncated MIDI chunk header."));
        }
        let len = read_length(chunk + 4);
        let end = (chunk + 8)
            .checked_add(len)
            .filter(|&e| e <= data.len())
            .ok_or_else(|| invalid("Truncated MIDI track."))?;
        if &data[chunk..chunk + 4] != b"MTrk" {
            chunk = end;
            continue;
        }
        let mut cursor = chunk + 8;
        let mut running = None;
        while cursor < end {
            vlq(&bytes, &mut cursor, end)?;
            if cursor >= end {
                return Err(invalid("Missing MIDI event."));
            }
            let status = if bytes[cursor] >= 0x80 {
                let status = bytes[cursor];
                cursor += 1;
                status
            } else {
                running
                    .ok_or_else(|| invalid("MIDI running status has no preceding channel event."))?
            };
            match status {
                0x80..=0xef => {
                    running = Some(status);
                    let count = if status & 0xf0 == 0xc0 || status & 0xf0 == 0xd0 {
                        1
                    } else {
                        2
                    };
                    if cursor + count > end {
                        return Err(invalid("Truncated MIDI channel message."));
                    }
                    for byte in &mut bytes[cursor..cursor + count] {
                        if *byte > 127 {
                            if !clip {
                                return Err(invalid("MIDI_INVALID_DATA_BYTE: MIDI 数据字节超出 0–127。可确认使用兼容修复模式后重试。"));
                            }
                            *byte = 127;
                        }
                    }
                    cursor += count;
                }
                0xff => {
                    // Match midly's event boundaries. Reusing channel running
                    // status after a meta event can misclassify later bytes.
                    running = None;
                    if cursor >= end {
                        return Err(invalid("Truncated MIDI meta event."));
                    }
                    let meta_type = bytes[cursor];
                    cursor += 1;
                    let length = vlq(&bytes, &mut cursor, end)?;
                    cursor = cursor
                        .checked_add(length)
                        .filter(|&c| c <= end)
                        .ok_or_else(|| invalid("Truncated MIDI meta payload."))?;
                    // Accept zero padding only after an explicit end-of-track.
                    if meta_type == 0x2f
                        && length == 0
                        && bytes[cursor..end].iter().all(|&byte| byte == 0)
                    {
                        break;
                    }
                }
                0xf0 | 0xf7 => {
                    let length = vlq(&bytes, &mut cursor, end)?;
                    cursor = cursor
                        .checked_add(length)
                        .filter(|&c| c <= end)
                        .ok_or_else(|| invalid("Truncated MIDI SysEx payload."))?;
                    running = None;
                }
                _ => return Err(invalid("Unsupported status in Standard MIDI File.")),
            }
        }
        complete_tracks += 1;
        chunk = end;
    }
    Ok(bytes)
}

pub fn decode_midi_text(bytes: &[u8]) -> String {
    if let Ok(text) = std::str::from_utf8(bytes) {
        return text.trim_matches('\0').to_string();
    }
    let score = |text: &str| -> i32 {
        text.chars()
            .map(|ch| {
                if ('\u{3400}'..='\u{9fff}').contains(&ch) {
                    50
                } else if ch == '\u{fffd}' {
                    -120
                } else if ch.is_control() {
                    -80
                } else if ch.is_alphanumeric() {
                    4
                } else {
                    1
                }
            })
            .sum()
    };
    let mut best = String::from_utf8_lossy(bytes).into_owned();
    let mut best_score = score(&best);
    for label in [
        b"gb18030".as_slice(),
        b"big5".as_slice(),
        b"shift_jis".as_slice(),
    ] {
        if let Some(encoding) = encoding_rs::Encoding::for_label(label) {
            let (text, _, errors) = encoding.decode(bytes);
            if !errors && score(&text) > best_score {
                best_score = score(&text);
                best = text.into_owned();
            }
        }
    }
    best.trim_matches('\0').to_string()
}

#[cfg(test)]
mod tests {
    use super::*;
    fn smf(track: &[u8]) -> Vec<u8> {
        let mut bytes = b"MThd\0\0\0\x06\0\0\0\x01\0\x60MTrk".to_vec();
        bytes.extend_from_slice(&(track.len() as u32).to_be_bytes());
        bytes.extend_from_slice(track);
        bytes
    }
    #[test]
    fn complete_file_zero_padding_is_accepted_without_modifying_bytes() {
        let original = smf(&[0, 0x90, 60, 64, 96, 0x80, 60, 0, 0, 0xff, 0x2f, 0]);
        let expected = crate::core::midi::MidiParser::parse_bytes(&original, 1.0).unwrap();
        for length in [1, 7, 8, 32] {
            let mut padded = original.clone();
            padded.extend(vec![0; length]);
            assert_eq!(validated_midi_bytes(&padded, false).unwrap(), padded);
            let actual = crate::core::midi::MidiParser::parse_bytes(&padded, 1.0).unwrap();
            assert_eq!(actual.0[0].notes.len(), expected.0[0].notes.len());
            assert_eq!(
                actual.0[0].notes[0].duration,
                expected.0[0].notes[0].duration
            );
            assert_eq!(actual.0[0].notes[0].pitch, 60);
        }
    }
    #[test]
    fn zero_padding_inside_track_requires_end_of_track() {
        let mut track = vec![0, 0x90, 60, 64, 96, 0x80, 60, 0, 0, 0xff, 0x2f, 0];
        track.extend([0; 3]);
        assert!(crate::core::midi::MidiParser::parse_bytes(&smf(&track), 1.0).is_ok());
        assert!(validated_midi_bytes(&smf(&[0, 0x90, 60, 64, 0]), false).is_err());
    }
    #[test]
    fn compatibility_never_hides_missing_structure() {
        let valid = smf(&[0, 0xff, 0x2f, 0]);
        for clip in [false, true] {
            for padding in [1, 8, 32] {
                let mut missing = valid.clone();
                missing[11] = 2;
                missing.extend(vec![0; padding]);
                assert!(validated_midi_bytes(&missing, clip).is_err());
            }
            let mut truncated = valid.clone();
            truncated.pop();
            assert!(validated_midi_bytes(&truncated, clip).is_err());
            let mut extra_header = valid.clone();
            extra_header.extend(b"MTrk");
            assert!(validated_midi_bytes(&extra_header, clip).is_err());
            assert!(validated_midi_bytes(&smf(&[0, 0xff, 1, 4, b'a']), clip).is_err());
        }
    }
    #[test]
    fn meta_and_sysex_payloads_are_not_channel_data_and_clear_running_status() {
        let payload = smf(&[
            0, 0xff, 1, 2, 0x80, 0xff, 0, 0xf0, 2, 0x80, 0xf7, 0, 0xff, 0x2f, 0,
        ]);
        assert_eq!(validated_midi_bytes(&payload, false).unwrap(), payload);
        for clip in [false, true] {
            let stale = smf(&[0, 0x90, 60, 64, 0, 0xff, 1, 0, 0, 61, 0x80]);
            let error = validated_midi_bytes(&stale, clip).unwrap_err().to_string();
            assert!(error.contains("running status"), "{error}");
        }
    }
    #[test]
    fn strict_rejects_and_explicit_clip_repairs_out_of_range_data() {
        let track = [
            0, 0xe0, 0, 0x80, 0, 0x90, 60, 64, 0x83, 0x60, 0x80, 60, 0, 0, 0xff, 0x2f, 0,
        ];
        let mut midi = b"MThd\0\0\0\x06\0\0\0\x01\x01\xe0MTrk".to_vec();
        midi.extend_from_slice(&(track.len() as u32).to_be_bytes());
        midi.extend_from_slice(&track);
        assert!(validated_midi_bytes(&midi, false)
            .unwrap_err()
            .to_string()
            .starts_with("MIDI_INVALID_DATA_BYTE"));
        let fixed = validated_midi_bytes(&midi, true).unwrap();
        assert_eq!(fixed[25], 127);
        assert_eq!(midi[25], 128);
        assert!(midly::Smf::parse(&fixed).is_ok());
    }
    #[test]
    fn chinese_track_names_are_recovered() {
        assert_eq!(decode_midi_text("星空钢琴".as_bytes()), "星空钢琴");
        let (bytes, _, _) = encoding_rs::GBK.encode("星空钢琴");
        assert_eq!(decode_midi_text(&bytes), "星空钢琴");
    }
}
