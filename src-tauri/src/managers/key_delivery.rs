use super::hotkey_manager::RawKey;
use std::collections::{HashMap, VecDeque};
use std::sync::Mutex;
use std::time::{Duration, Instant};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum KeySource {
    GlobalHook,
    Page,
}
struct Seen {
    source: KeySource,
    at: Instant,
    save_pending: bool,
}
#[derive(Default)]
pub struct KeyDelivery {
    seen: Mutex<HashMap<(RawKey, bool), VecDeque<Seen>>>,
}
impl KeyDelivery {
    /// Serialize both paths, pair corresponding events, and confirm global save only in the page.
    pub fn deliver(
        &self,
        raw: RawKey,
        pressed: bool,
        source: KeySource,
        action: impl FnOnce() -> bool,
    ) -> bool {
        self.deliver_at(raw, pressed, source, Instant::now(), action)
    }
    fn deliver_at(
        &self,
        raw: RawKey,
        pressed: bool,
        source: KeySource,
        now: Instant,
        action: impl FnOnce() -> bool,
    ) -> bool {
        let mut memory = self.seen.lock().unwrap_or_else(|e| e.into_inner());
        let queue = memory.entry((raw, pressed)).or_default();
        while queue
            .front()
            .is_some_and(|e| now.saturating_duration_since(e.at) > Duration::from_millis(250))
        {
            queue.pop_front();
        }
        if queue.front().is_some_and(|e| e.source != source) {
            let seen = queue.pop_front().unwrap();
            return source == KeySource::Page && seen.save_pending;
        }
        let save_pending = action();
        if queue.len() >= 128 {
            queue.pop_front();
        }
        queue.push_back(Seen {
            source,
            at: now,
            save_pending,
        });
        false
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::Cell;
    #[test]
    fn both_arrival_orders_deliver_once_and_next_physical_press_still_delivers() {
        for first in [KeySource::Page, KeySource::GlobalHook] {
            let gate = KeyDelivery::default();
            let count = Cell::new(0);
            let other = if first == KeySource::Page {
                KeySource::GlobalHook
            } else {
                KeySource::Page
            };
            for _ in 0..3 {
                for source in [first, other] {
                    gate.deliver(RawKey::Named("F6"), true, source, || {
                        count.set(count.get() + 1);
                        false
                    });
                    gate.deliver(RawKey::Named("F6"), false, source, || false);
                }
            }
            assert_eq!(count.get(), 3);
        }
    }
    #[test]
    fn a_global_save_is_confirmed_once_by_its_page_event() {
        let gate = KeyDelivery::default();
        assert!(!gate.deliver(RawKey::Char('s'), true, KeySource::GlobalHook, || true));
        assert!(
            gate.deliver(RawKey::Char('s'), true, KeySource::Page, || panic!(
                "duplicate"
            ))
        );
        assert!(!gate.deliver(RawKey::Char('s'), false, KeySource::GlobalHook, || false));
        assert!(
            !gate.deliver(RawKey::Char('s'), false, KeySource::Page, || panic!(
                "duplicate"
            ))
        );
    }
    #[test]
    fn page_first_save_and_injected_echo_do_not_execute_twice() {
        let gate = KeyDelivery::default();
        assert!(!gate.deliver(RawKey::Char('s'), true, KeySource::Page, || false));
        assert!(
            !gate.deliver(RawKey::Char('s'), true, KeySource::GlobalHook, || panic!(
                "duplicate"
            ))
        );
        assert!(!gate.deliver(RawKey::Named("F6"), true, KeySource::GlobalHook, || false));
        assert!(
            !gate.deliver(RawKey::Named("F6"), true, KeySource::Page, || panic!(
                "echo duplicate"
            ))
        );
    }
    #[test]
    fn left_and_right_modifiers_are_distinct_physical_events() {
        use super::super::hotkey_manager::Modifier;
        let gate = KeyDelivery::default();
        let count = Cell::new(0);
        for (raw, source) in [
            (RawKey::ModLeft(Modifier::Ctrl), KeySource::GlobalHook),
            (RawKey::ModRight(Modifier::Ctrl), KeySource::Page),
            (RawKey::ModLeft(Modifier::Ctrl), KeySource::Page),
            (RawKey::ModRight(Modifier::Ctrl), KeySource::GlobalHook),
        ] {
            gate.deliver(raw, true, source, || {
                count.set(count.get() + 1);
                false
            });
        }
        assert_eq!(count.get(), 2);
    }
    #[test]
    fn a_stale_hook_press_cannot_save_in_a_later_window_press() {
        let gate = KeyDelivery::default();
        let now = Instant::now();
        let count = Cell::new(0);
        gate.deliver_at(RawKey::Char('s'), true, KeySource::GlobalHook, now, || true);
        assert!(!gate.deliver_at(
            RawKey::Char('s'),
            true,
            KeySource::Page,
            now + Duration::from_millis(300),
            || {
                count.set(1);
                false
            }
        ));
        assert_eq!(count.get(), 1);
    }
}
