use std::collections::HashSet;

use crate::core::keyboard_driver::{Key, KeyActionResult, KeyboardDriver};

/// This is an application setting, not a per-song musical compilation option.
pub fn pause_on_focus(config: &serde_json::Value) -> bool {
    config
        .get("pause_on_app_focus")
        .and_then(|v| v.as_bool())
        .unwrap_or(false)
}

pub fn auto_focus_roblox(config: &serde_json::Value) -> bool {
    config
        .get("auto_focus_roblox")
        .and_then(|v| v.as_bool())
        .unwrap_or(false)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ActivationResult {
    Disabled,
    Focused,
    NotFound,
    Denied,
    Unsupported,
    Cancelled,
}

impl ActivationResult {
    pub fn failure_message(self) -> Option<&'static str> {
        match self {
            Self::NotFound => Some("No Roblox game window was found. Playback is paused. Open Roblox and use the playback shortcut to retry."),
            Self::Denied => Some("Windows did not switch focus to Roblox. Playback is paused. Focus the game manually and use the playback shortcut to retry."),
            Self::Unsupported => Some("Automatic Roblox window focus is only supported on Windows. Playback is paused."),
            _ => None,
        }
    }
}

fn is_roblox_player(image: &str) -> bool {
    let name = image.rsplit(['\\', '/']).next().unwrap_or("");
    name.eq_ignore_ascii_case("RobloxPlayerBeta.exe")
        || name.eq_ignore_ascii_case("RobloxPlayer.exe")
}

pub fn activate_roblox_window(cancel: &std::sync::atomic::AtomicBool) -> ActivationResult {
    if cancel.load(std::sync::atomic::Ordering::Relaxed) {
        return ActivationResult::Cancelled;
    }
    #[cfg(windows)]
    {
        native::activate(cancel)
    }
    #[cfg(not(windows))]
    {
        ActivationResult::Unsupported
    }
}

#[cfg(windows)]
mod native {
    use super::*;
    use std::{
        ptr::null_mut,
        sync::atomic::{AtomicBool, Ordering},
        time::Duration,
    };
    use windows_sys::Win32::{
        Foundation::{CloseHandle, HWND, LPARAM},
        System::Threading::{
            OpenProcess, QueryFullProcessImageNameW, PROCESS_QUERY_LIMITED_INFORMATION,
        },
        UI::WindowsAndMessaging::{
            EnumWindows, GetForegroundWindow, GetWindow, GetWindowThreadProcessId, IsIconic,
            IsWindow, IsWindowVisible, SetForegroundWindow, ShowWindowAsync, GW_OWNER, SW_RESTORE,
        },
    };

    fn player_window(window: HWND) -> bool {
        unsafe {
            let mut pid = 0;
            GetWindowThreadProcessId(window, &mut pid);
            if pid == 0 {
                return false;
            }
            let process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid);
            if process.is_null() {
                return false;
            }
            let mut path = vec![0u16; 32768];
            let mut size = path.len() as u32;
            let ok = QueryFullProcessImageNameW(process, 0, path.as_mut_ptr(), &mut size);
            CloseHandle(process);
            ok != 0 && is_roblox_player(&String::from_utf16_lossy(&path[..size as usize]))
        }
    }

    unsafe extern "system" fn find_window(window: HWND, result: LPARAM) -> i32 {
        if IsWindowVisible(window) != 0
            && GetWindow(window, GW_OWNER).is_null()
            && player_window(window)
        {
            *(result as *mut HWND) = window;
            return 0;
        }
        1
    }

    pub(super) fn activate(cancel: &AtomicBool) -> ActivationResult {
        unsafe {
            let foreground = GetForegroundWindow();
            if !foreground.is_null() && player_window(foreground) {
                return ActivationResult::Focused;
            }
            let mut target: HWND = null_mut();
            EnumWindows(Some(find_window), &mut target as *mut HWND as LPARAM);
            if cancel.load(Ordering::Relaxed) {
                return ActivationResult::Cancelled;
            }
            if target.is_null() || IsWindow(target) == 0 {
                return ActivationResult::NotFound;
            }
            if IsIconic(target) != 0 {
                ShowWindowAsync(target, SW_RESTORE);
            }
            // Windows may deliver foreground activation asynchronously. Do not
            // inject notes or check HuMidi's focus policy until it is confirmed.
            SetForegroundWindow(target);
            for _ in 0..40 {
                if cancel.load(Ordering::Relaxed) {
                    return ActivationResult::Cancelled;
                }
                let current = GetForegroundWindow();
                if !current.is_null() && IsIconic(current) == 0 && (current == target || player_window(current)) {
                    return ActivationResult::Focused;
                }
                std::thread::sleep(Duration::from_millis(20));
            }
            ActivationResult::Denied
        }
    }
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
    fn focus_options_default_off_and_keep_explicit_saved_choices() {
        assert!(!pause_on_focus(&serde_json::json!({})));
        assert!(!pause_on_focus(
            &serde_json::json!({"pause_on_app_focus": null})
        ));
        assert!(!pause_on_focus(
            &serde_json::json!({"pause_on_app_focus": false})
        ));
        assert!(pause_on_focus(
            &serde_json::json!({"pause_on_app_focus": true})
        ));
        assert!(!auto_focus_roblox(&serde_json::json!({})));
        assert!(!auto_focus_roblox(
            &serde_json::json!({"auto_focus_roblox": null})
        ));
        assert!(auto_focus_roblox(
            &serde_json::json!({"auto_focus_roblox": true})
        ));
    }

    #[test]
    fn identifies_player_processes_without_matching_browsers_studio_or_launchers() {
        assert!(is_roblox_player(
            r"C:\Roblox\Versions\v1\RobloxPlayerBeta.exe"
        ));
        assert!(is_roblox_player("ROBLOXPLAYER.EXE"));
        for name in [
            "chrome.exe",
            "RobloxStudioBeta.exe",
            "RobloxPlayerLauncher.exe",
            "RobloxPlayerBeta.exe.backup",
            "Roblox",
        ] {
            assert!(!is_roblox_player(name));
        }
    }

    #[test]
    fn cancelled_activation_does_not_enumerate_or_switch_any_window() {
        assert_eq!(
            activate_roblox_window(&std::sync::atomic::AtomicBool::new(true)),
            ActivationResult::Cancelled
        );
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
