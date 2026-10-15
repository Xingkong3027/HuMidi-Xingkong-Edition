use std::collections::HashSet;

use crate::core::keyboard_driver::{Key, KeyActionResult, KeyboardDriver};

/// This is an application setting, not a per-song musical compilation option.
pub fn pause_on_focus(config: &serde_json::Value) -> bool {
    config
        .get("pause_on_app_focus")
        .and_then(|v| v.as_bool())
        .unwrap_or(true)
}

pub fn app_has_focus<R: tauri::Runtime>(app: &tauri::AppHandle<R>) -> bool {
    #[cfg(windows)]
    {
        let _ = app;
        // Query the actual foreground process instead of waiting for a WebView
        // focus notification, which may arrive after the first injected key.
        unsafe {
            use windows_sys::Win32::UI::WindowsAndMessaging::{
                GetForegroundWindow, GetWindowThreadProcessId,
            };
            let window = GetForegroundWindow();
            if window.is_null() {
                return false;
            }
            let mut process = 0;
            GetWindowThreadProcessId(window, &mut process);
            process == std::process::id()
        }
    }
    #[cfg(not(windows))]
    {
        use tauri::Manager;
        app.webview_windows()
            .values()
            .any(|window| window.is_focused().unwrap_or(false))
    }
}

/// Never type performance notes/pedal into our own controls. Releases of keys
/// actually sent elsewhere still go through so focus changes cannot strand them.
pub struct FocusedInputDriver<D, F> {
    inner: D,
    focused: F,
    held: HashSet<Key>,
}

impl<D, F> FocusedInputDriver<D, F> {
    pub fn new(inner: D, focused: F) -> Self {
        Self {
            inner,
            focused,
            held: HashSet::new(),
        }
    }
}

impl<D: KeyboardDriver, F: Fn() -> bool> KeyboardDriver for FocusedInputDriver<D, F> {
    fn press(&mut self, key: Key) -> KeyActionResult {
        if (self.focused)() {
            return Ok(());
        }
        self.inner.press(key)?;
        self.held.insert(key);
        Ok(())
    }

    fn release(&mut self, key: Key) -> KeyActionResult {
        if (self.focused)() && !self.held.contains(&key) {
            return Ok(());
        }
        self.inner.release(key)?;
        self.held.remove(&key);
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::{Cell, RefCell};

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

    #[test]
    fn defaults_to_pause_but_accepts_continue_setting() {
        assert!(pause_on_focus(&serde_json::json!({})));
        assert!(pause_on_focus(
            &serde_json::json!({"pause_on_app_focus": null})
        ));
        assert!(!pause_on_focus(
            &serde_json::json!({"pause_on_app_focus": false})
        ));
    }

    #[test]
    fn focused_window_receives_no_note_or_pedal_presses() {
        let log = RefCell::new(Vec::new());
        let focused = Cell::new(true);
        let mut driver = FocusedInputDriver::new(Driver(&log), || focused.get());
        for key in [Key::Space, Key::Ctrl, Key::Shift, Key::Alt, Key::Char('s')] {
            driver.press(key).unwrap();
            driver.release(key).unwrap();
        }
        assert!(log.borrow().is_empty());
        focused.set(false);
        driver.press(Key::Char('g')).unwrap();
        driver.release(Key::Char('g')).unwrap();
        assert_eq!(
            *log.borrow(),
            vec![(Key::Char('g'), true), (Key::Char('g'), false)]
        );
    }

    #[test]
    fn releases_previously_sent_keys_after_focus_returns() {
        let log = RefCell::new(Vec::new());
        let focused = Cell::new(false);
        let mut driver = FocusedInputDriver::new(Driver(&log), || focused.get());
        driver.press(Key::Space).unwrap();
        driver.press(Key::Ctrl).unwrap();
        focused.set(true);
        driver.release(Key::Space).unwrap();
        driver.release(Key::Ctrl).unwrap();
        driver.release(Key::Space).unwrap();
        assert_eq!(
            *log.borrow(),
            vec![
                (Key::Space, true),
                (Key::Ctrl, true),
                (Key::Space, false),
                (Key::Ctrl, false)
            ]
        );
    }
}
