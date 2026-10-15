use humidi_tauri_lib::{
    commands::run_playback_loop_with_activation,
    core::{
        config::PlaybackConfig,
        keyboard_driver::{Key, KeyActionResult, KeyboardDriver},
        models::KeyEvent,
        player::{PlaybackEngine, PlayerEvent},
    },
    managers::window_focus::ActivationResult,
    state::PlaybackCommand,
};
use std::{
    cell::{Cell, RefCell},
    sync::mpsc,
};

struct Driver<'a> {
    log: &'a RefCell<Vec<(Key, bool, f64)>>,
    time: &'a Cell<f64>,
}
impl KeyboardDriver for Driver<'_> {
    fn press(&mut self, key: Key) -> KeyActionResult {
        self.log.borrow_mut().push((key, true, self.time.get()));
        Ok(())
    }
    fn release(&mut self, key: Key) -> KeyActionResult {
        self.log.borrow_mut().push((key, false, self.time.get()));
        Ok(())
    }
}
fn engine(countdown: bool) -> PlaybackEngine {
    let mut engine = PlaybackEngine::new(
        PlaybackConfig {
            countdown,
            countdown_seconds: 1,
            auto_pause: false,
            ..Default::default()
        },
        vec![],
    );
    engine.load_compiled_events(
        vec![
            KeyEvent::new(0.0, 1, "pedal", "down"),
            KeyEvent::new(0.2, 2, "pedal", "up"),
        ],
        0.2,
    );
    engine
}

#[test]
fn all_switch_combinations_check_focus_only_after_activation_and_start_the_clock_after_waiting() {
    for auto in [false, true] {
        for pause in [false, true] {
            for countdown in [false, true] {
                let time = Cell::new(0.0);
                let focused = Cell::new(true);
                let calls = Cell::new(0);
                let ready_at = Cell::new(0.0);
                let log = RefCell::new(vec![]);
                let events = RefCell::new(vec![]);
                let mut driver = Driver {
                    log: &log,
                    time: &time,
                };
                let (tx, rx) = mpsc::channel();
                run_playback_loop_with_activation(
                    engine(countdown),
                    &mut driver,
                    &rx,
                    |ev| events.borrow_mut().push(ev.clone()),
                    || time.get(),
                    |dt| {
                        time.set(time.get() + dt.max(0.01));
                        if time.get() > 2.0 {
                            tx.send(PlaybackCommand::Stop).unwrap();
                        }
                        assert!(time.get() < 3.0);
                    },
                    || pause && focused.get(),
                    || {
                        calls.set(calls.get() + 1);
                        if auto {
                            time.set(time.get() + 0.25);
                            focused.set(false);
                            ready_at.set(time.get());
                            ActivationResult::Focused
                        } else {
                            ActivationResult::Disabled
                        }
                    },
                );
                let events = events.into_inner();
                let expected_pause = usize::from(pause && !auto);
                assert_eq!(
                    events
                        .iter()
                        .filter(|e| **e == PlayerEvent::FocusPaused)
                        .count(),
                    expected_pause,
                    "auto={auto},pause={pause},countdown={countdown}"
                );
                assert_eq!(calls.get(), 1, "no repeated activation while playing");
                if expected_pause == 0 {
                    assert_eq!(
                        events
                            .iter()
                            .filter(|e| **e == PlayerEvent::NaturalFinished)
                            .count(),
                        1
                    );
                    if auto {
                        assert_eq!(
                            log.borrow().iter().find(|(_, down, _)| *down).unwrap().2,
                            ready_at.get(),
                            "first note must not be skipped by activation time"
                        );
                    }
                } else {
                    assert!(!events.contains(&PlayerEvent::NaturalFinished));
                    assert!(!log.borrow().iter().any(|(_, down, _)| *down));
                }
            }
        }
    }
}

#[test]
fn returning_to_humidi_pauses_once_and_manual_resume_activates_before_unpausing() {
    let time = Cell::new(0.0);
    let focused = Cell::new(true);
    let calls = Cell::new(0);
    let requested_resume = Cell::new(false);
    let log = RefCell::new(vec![]);
    let events = RefCell::new(vec![]);
    let mut driver = Driver {
        log: &log,
        time: &time,
    };
    let (tx, rx) = mpsc::channel();
    run_playback_loop_with_activation(
        engine(false),
        &mut driver,
        &rx,
        |ev| events.borrow_mut().push(ev.clone()),
        || time.get(),
        |dt| {
            time.set(time.get() + dt.max(0.01));
            if !requested_resume.get() && time.get() > 0.03 {
                focused.set(true);
            }
            if !requested_resume.get() && time.get() > 0.5 {
                requested_resume.set(true);
                tx.send(PlaybackCommand::TogglePause).unwrap();
            }
            assert!(time.get() < 3.0);
        },
        || focused.get(),
        || {
            calls.set(calls.get() + 1);
            focused.set(false);
            time.set(time.get() + 0.02);
            ActivationResult::Focused
        },
    );
    let events = events.into_inner();
    assert_eq!(calls.get(), 2);
    assert_eq!(
        events
            .iter()
            .filter(|e| **e == PlayerEvent::FocusPaused)
            .count(),
        1
    );
    assert_eq!(
        events
            .iter()
            .filter(|e| **e == PlayerEvent::NaturalFinished)
            .count(),
        1
    );
}

#[test]
fn failed_activation_pauses_even_when_focus_pause_is_off_and_never_skips_songs() {
    for result in [
        ActivationResult::NotFound,
        ActivationResult::Denied,
        ActivationResult::Unsupported,
    ] {
        let time = Cell::new(0.0);
        let calls = Cell::new(0);
        let log = RefCell::new(vec![]);
        let events = RefCell::new(vec![]);
        let mut driver = Driver {
            log: &log,
            time: &time,
        };
        let (tx, rx) = mpsc::channel();
        run_playback_loop_with_activation(
            engine(false),
            &mut driver,
            &rx,
            |ev| events.borrow_mut().push(ev.clone()),
            || time.get(),
            |dt| {
                time.set(time.get() + dt.max(0.01));
                if time.get() > 1.0 {
                    tx.send(PlaybackCommand::Stop).unwrap();
                }
            },
            || false,
            || {
                calls.set(calls.get() + 1);
                result
            },
        );
        let events = events.into_inner();
        assert_eq!(calls.get(), 1);
        assert_eq!(
            events
                .iter()
                .filter(|e| **e == PlayerEvent::FocusPaused)
                .count(),
            1
        );
        assert!(!events.contains(&PlayerEvent::NaturalFinished));
        assert!(!log.borrow().iter().any(|(_, down, _)| *down));
        assert!(events.iter().any(|e|matches!(e,PlayerEvent::Status(message) if message==result.failure_message().unwrap())));
    }
}

#[test]
fn missing_game_can_be_retried_manually_without_restarting_the_song() {
    let time = Cell::new(0.0);
    let calls = Cell::new(0);
    let requested = Cell::new(false);
    let log = RefCell::new(vec![]);
    let events = RefCell::new(vec![]);
    let mut driver = Driver {
        log: &log,
        time: &time,
    };
    let (tx, rx) = mpsc::channel();
    run_playback_loop_with_activation(
        engine(false),
        &mut driver,
        &rx,
        |ev| events.borrow_mut().push(ev.clone()),
        || time.get(),
        |dt| {
            time.set(time.get() + dt.max(0.01));
            if !requested.get() && time.get() > 0.5 {
                requested.set(true);
                tx.send(PlaybackCommand::TogglePause).unwrap();
            }
            assert!(time.get() < 3.0);
        },
        || false,
        || {
            calls.set(calls.get() + 1);
            if calls.get() == 1 {
                ActivationResult::NotFound
            } else {
                ActivationResult::Focused
            }
        },
    );
    let events = events.into_inner();
    assert_eq!(calls.get(), 2);
    assert_eq!(
        events
            .iter()
            .filter(|e| **e == PlayerEvent::FocusPaused)
            .count(),
        1
    );
    assert!(events.contains(&PlayerEvent::NaturalFinished));
    assert!(log.borrow().iter().find(|(_, down, _)| *down).unwrap().2 >= 0.5);
}

#[test]
fn cancelled_activation_stops_without_a_focus_pause_or_natural_completion() {
    let time = Cell::new(0.0);
    let log = RefCell::new(vec![]);
    let events = RefCell::new(vec![]);
    let mut driver = Driver {
        log: &log,
        time: &time,
    };
    let (_tx, rx) = mpsc::channel();
    run_playback_loop_with_activation(
        engine(false),
        &mut driver,
        &rx,
        |ev| events.borrow_mut().push(ev.clone()),
        || time.get(),
        |_| panic!("cancelled start must finish immediately"),
        || true,
        || ActivationResult::Cancelled,
    );
    let events = events.into_inner();
    assert!(!events.contains(&PlayerEvent::FocusPaused));
    assert!(!events.contains(&PlayerEvent::NaturalFinished));
    assert!(events.contains(&PlayerEvent::Finished));
    assert!(!log.borrow().iter().any(|(_, down, _)| *down));
}

#[test]
fn stop_during_countdown_does_not_activate_roblox() {
    let time = Cell::new(0.0);
    let log = RefCell::new(vec![]);
    let events = RefCell::new(vec![]);
    let mut driver = Driver {
        log: &log,
        time: &time,
    };
    let (tx, rx) = mpsc::channel();
    tx.send(PlaybackCommand::Stop).unwrap();
    run_playback_loop_with_activation(
        engine(true),
        &mut driver,
        &rx,
        |ev| events.borrow_mut().push(ev.clone()),
        || time.get(),
        |_| {},
        || false,
        || panic!("cancelled countdown must not steal focus"),
    );
    assert!(events.borrow().contains(&PlayerEvent::Finished));
    assert!(!events.borrow().contains(&PlayerEvent::NaturalFinished));
}
