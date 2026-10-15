use humidi_tauri_lib::{
    commands::run_playback_loop_with_focus,
    core::{
        config::PlaybackConfig,
        keyboard_driver::{Key, KeyActionResult, KeyboardDriver},
        models::KeyEvent,
        player::{PlaybackEngine, PlayerEvent},
    },
    managers::window_focus::FocusedInputDriver,
    state::PlaybackCommand,
};
use std::{
    cell::{Cell, RefCell},
    sync::mpsc,
};

struct Driver<'a>(&'a RefCell<Vec<(Key, bool)>>);
impl KeyboardDriver for Driver<'_> {
    fn press(&mut self, key: Key) -> KeyActionResult {
        self.0.borrow_mut().push((key, true));
        Ok(())
    }
    fn release(&mut self, key: Key) -> KeyActionResult {
        self.0.borrow_mut().push((key, false));
        Ok(())
    }
}

fn engine(countdown: bool) -> PlaybackEngine {
    let config = PlaybackConfig {
        countdown,
        countdown_seconds: 1,
        auto_pause: false,
        ..Default::default()
    };
    let mut engine = PlaybackEngine::new(config, vec![]);
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
fn focused_start_pauses_once_without_typing_or_advancing_the_playlist() {
    let log = RefCell::new(vec![]);
    let mut driver = FocusedInputDriver::new(Driver(&log), || true);
    let (tx, rx) = mpsc::channel();
    let events = RefCell::new(vec![]);
    let time = Cell::new(0.0);
    run_playback_loop_with_focus(
        engine(false),
        &mut driver,
        &rx,
        |ev| events.borrow_mut().push(ev.clone()),
        || time.get(),
        |dt| {
            time.set(time.get() + dt.max(0.01));
            if time.get() > 2.0 {
                tx.send(PlaybackCommand::Stop).unwrap();
            }
        },
        || true,
    );
    let events = events.into_inner();
    assert_eq!(
        events
            .iter()
            .filter(|e| **e == PlayerEvent::FocusPaused)
            .count(),
        1
    );
    assert!(!events.contains(&PlayerEvent::NaturalFinished));
    assert!(!events.contains(&PlayerEvent::AutoPaused));
    assert!(log.borrow().is_empty());
}

#[test]
fn continue_policy_keeps_time_but_never_types_into_the_focused_application() {
    let log = RefCell::new(vec![]);
    let mut driver = FocusedInputDriver::new(Driver(&log), || true);
    let (_tx, rx) = mpsc::channel();
    let events = RefCell::new(vec![]);
    let time = Cell::new(0.0);
    run_playback_loop_with_focus(
        engine(false),
        &mut driver,
        &rx,
        |ev| events.borrow_mut().push(ev.clone()),
        || time.get(),
        |dt| {
            time.set(time.get() + dt.max(0.01));
            assert!(time.get() < 3.0);
        },
        || false,
    );
    let events = events.into_inner();
    assert_eq!(
        events
            .iter()
            .filter(|e| **e == PlayerEvent::NaturalFinished)
            .count(),
        1
    );
    assert!(!events.contains(&PlayerEvent::FocusPaused));
    assert!(log.borrow().is_empty());
}

#[test]
fn focus_pause_releases_held_pedal_and_only_finishes_after_explicit_resume() {
    let log = RefCell::new(vec![]);
    let time = Cell::new(0.0);
    let focused = Cell::new(false);
    let mut driver = FocusedInputDriver::new(Driver(&log), || focused.get());
    let (tx, rx) = mpsc::channel();
    let events = RefCell::new(vec![]);
    let resumed = Cell::new(false);
    run_playback_loop_with_focus(
        engine(false),
        &mut driver,
        &rx,
        |ev| {
            if *ev == PlayerEvent::NaturalFinished {
                assert!(resumed.get());
            }
            events.borrow_mut().push(ev.clone());
        },
        || time.get(),
        |dt| {
            time.set(time.get() + dt.max(0.01));
            if !resumed.get() && time.get() > 0.02 {
                focused.set(true);
            }
            if !resumed.get() && time.get() > 1.0 {
                focused.set(false);
                resumed.set(true);
                tx.send(PlaybackCommand::TogglePause).unwrap();
            }
            assert!(time.get() < 4.0);
        },
        || focused.get(),
    );
    let events = events.into_inner();
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
    assert!(log.borrow().contains(&(Key::Space, false)));
}

#[test]
fn countdown_allows_switching_to_the_target_window_before_focus_is_checked() {
    let log = RefCell::new(vec![]);
    let time = Cell::new(0.0);
    let mut driver = FocusedInputDriver::new(Driver(&log), || time.get() < 0.5);
    let (_tx, rx) = mpsc::channel();
    let events = RefCell::new(vec![]);
    run_playback_loop_with_focus(
        engine(true),
        &mut driver,
        &rx,
        |ev| events.borrow_mut().push(ev.clone()),
        || time.get(),
        |dt| {
            time.set(time.get() + dt.max(0.01));
            assert!(time.get() < 4.0);
        },
        || time.get() < 0.5,
    );
    let events = events.into_inner();
    assert!(!events.contains(&PlayerEvent::FocusPaused));
    assert!(events.contains(&PlayerEvent::NaturalFinished));
    assert!(log.borrow().contains(&(Key::Space, true)));
}
