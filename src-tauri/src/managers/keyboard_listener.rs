//! Windows hooks only enqueue keys. Routing and configuration I/O run on a worker.
use super::hotkey_manager::{Modifier, RawKey};

pub fn windows_key(vk: u32, scan: u32, extended: bool) -> Option<RawKey> {
    Some(match vk {
        0x30..=0x39 | 0x41..=0x5a => RawKey::Char(char::from_u32(vk)?.to_ascii_lowercase()),
        0x70..=0x87 => RawKey::Named(super::hotkey_manager::function_key_name(
            (vk - 0x70 + 1) as usize,
        )?),
        0xa0 => RawKey::ModLeft(Modifier::Shift),
        0xa1 => RawKey::ModRight(Modifier::Shift),
        0xa2 => RawKey::ModLeft(Modifier::Ctrl),
        0xa3 => RawKey::ModRight(Modifier::Ctrl),
        0xa4 => RawKey::ModLeft(Modifier::Alt),
        0xa5 => RawKey::ModRight(Modifier::Alt),
        0x10 if scan == 0x36 => RawKey::ModRight(Modifier::Shift),
        0x10 => RawKey::ModLeft(Modifier::Shift),
        0x11 if extended => RawKey::ModRight(Modifier::Ctrl),
        0x11 => RawKey::ModLeft(Modifier::Ctrl),
        0x12 if extended => RawKey::ModRight(Modifier::Alt),
        0x12 => RawKey::ModLeft(Modifier::Alt),
        0x5b => RawKey::ModLeft(Modifier::Cmd),
        0x5c => RawKey::ModRight(Modifier::Cmd),
        0xb0 => RawKey::Named("MediaNext"),
        0xb1 => RawKey::Named("MediaPrevious"),
        0xb2 => RawKey::Named("MediaStop"),
        0xb3 => RawKey::Named("MediaPlayPause"),
        0xad => RawKey::Named("VolumeMute"),
        0xae => RawKey::Named("VolumeDown"),
        0xaf => RawKey::Named("VolumeUp"),
        0x20 => RawKey::Named("Space"),
        0x1b => RawKey::Named("Escape"),
        0x09 => RawKey::Named("Tab"),
        0x0d if extended => RawKey::Named("NumEnter"),
        0x0d => RawKey::Named("Enter"),
        0x08 => RawKey::Named("Backspace"),
        0x2e => RawKey::Named("Delete"),
        0x2d => RawKey::Named("Insert"),
        0x26 => RawKey::Named("Up"),
        0x28 => RawKey::Named("Down"),
        0x25 => RawKey::Named("Left"),
        0x27 => RawKey::Named("Right"),
        0x24 => RawKey::Named("Home"),
        0x23 => RawKey::Named("End"),
        0x21 => RawKey::Named("PageUp"),
        0x22 => RawKey::Named("PageDown"),
        0x14 => RawKey::Named("CapsLock"),
        0x90 => RawKey::Named("NumLock"),
        0x91 => RawKey::Named("ScrollLock"),
        0x13 => RawKey::Named("Pause"),
        0x2c => RawKey::Named("PrintScreen"),
        0x60..=0x69 => RawKey::Named(
            [
                "Num0", "Num1", "Num2", "Num3", "Num4", "Num5", "Num6", "Num7", "Num8", "Num9",
            ][(vk - 0x60) as usize],
        ),
        0x6e => RawKey::Named("NumDecimal"),
        0x6b => RawKey::Named("NumAdd"),
        0x6d => RawKey::Named("NumSubtract"),
        0x6a => RawKey::Named("NumMultiply"),
        0x6f => RawKey::Named("NumDivide"),
        0xbd => RawKey::Char('-'),
        0xbb => RawKey::Char('='),
        0xdb => RawKey::Char('['),
        0xdd => RawKey::Char(']'),
        0xdc => RawKey::Char('\\'),
        0xba => RawKey::Char(';'),
        0xde => RawKey::Char('\''),
        0xbc => RawKey::Char(','),
        0xbe => RawKey::Char('.'),
        0xbf => RawKey::Char('/'),
        0xc0 => RawKey::Char('`'),
        _ => return None,
    })
}

#[cfg(not(windows))]
pub fn listen(mut callback: impl FnMut(RawKey, bool) + Send + 'static) -> Result<(), String> {
    rdev::listen(move |event| {
        let (key, press) = match event.event_type {
            rdev::EventType::KeyPress(key) => (key, true),
            rdev::EventType::KeyRelease(key) => (key, false),
            _ => return,
        };
        if let Some(raw) = super::hotkey_manager::rdev_key_to_raw(key) {
            callback(raw, press);
        }
    })
    .map_err(|error| format!("{error:?}"))
}

#[cfg(windows)]
pub fn listen(mut callback: impl FnMut(RawKey, bool) + Send + 'static) -> Result<(), String> {
    let (listener, events) = native::Listener::start()?;
    for (raw, press) in events {
        callback(raw, press);
    }
    drop(listener);
    Err("Keyboard listener stopped".into())
}

#[cfg(windows)]
mod native {
    use super::*;
    use std::{
        cell::RefCell,
        ptr::null_mut,
        sync::mpsc::{self, Receiver, Sender},
        thread::{self, JoinHandle},
    };
    use windows_sys::Win32::{
        Foundation::{LPARAM, LRESULT, WPARAM},
        System::{LibraryLoader::GetModuleHandleW, Threading::GetCurrentThreadId},
        UI::WindowsAndMessaging::*,
    };
    thread_local! { static EVENTS: RefCell<Option<Sender<(RawKey,bool)>>> = const { RefCell::new(None) }; }
    unsafe extern "system" fn hook(code: i32, message: WPARAM, data: LPARAM) -> LRESULT {
        if code == HC_ACTION as i32 {
            let press = match message as u32 {
                WM_KEYDOWN | WM_SYSKEYDOWN => Some(true),
                WM_KEYUP | WM_SYSKEYUP => Some(false),
                _ => None,
            };
            if let Some(press) = press {
                let key = &*(data as *const KBDLLHOOKSTRUCT);
                if let Some(raw) =
                    windows_key(key.vkCode, key.scanCode, key.flags & LLKHF_EXTENDED != 0)
                {
                    EVENTS.with(|events| {
                        if let Some(tx) = events.borrow().as_ref() {
                            let _ = tx.send((raw, press));
                        }
                    });
                }
            }
        }
        // Never swallow input or alter other applications' keyboard behavior.
        CallNextHookEx(null_mut(), code, message, data)
    }
    pub(super) struct Listener {
        id: u32,
        thread: Option<JoinHandle<()>>,
    }
    impl Listener {
        pub(super) fn start() -> Result<(Self, Receiver<(RawKey, bool)>), String> {
            let (tx, rx) = mpsc::channel();
            let (ready_tx, ready_rx) = mpsc::sync_channel(1);
            let thread = thread::spawn(move || unsafe {
                // Establish the queue before publishing the thread ID.
                let mut msg: MSG = std::mem::zeroed();
                PeekMessageW(&mut msg, null_mut(), 0, 0, PM_NOREMOVE);
                EVENTS.with(|events| *events.borrow_mut() = Some(tx));
                let handle = SetWindowsHookExW(
                    WH_KEYBOARD_LL,
                    Some(hook),
                    GetModuleHandleW(std::ptr::null()),
                    0,
                );
                if handle.is_null() {
                    let _ = ready_tx.send(Err(std::io::Error::last_os_error().to_string()));
                    EVENTS.with(|events| *events.borrow_mut() = None);
                    return;
                }
                let _ = ready_tx.send(Ok(GetCurrentThreadId()));
                loop {
                    // GetMessage requires a real MSG buffer and a persistent loop.
                    let result = GetMessageW(&mut msg, null_mut(), 0, 0);
                    if result <= 0 {
                        break;
                    }
                    TranslateMessage(&msg);
                    DispatchMessageW(&msg);
                }
                UnhookWindowsHookEx(handle);
                EVENTS.with(|events| *events.borrow_mut() = None);
            });
            match ready_rx.recv().map_err(|e| e.to_string())? {
                Ok(id) => Ok((
                    Self {
                        id,
                        thread: Some(thread),
                    },
                    rx,
                )),
                Err(error) => {
                    let _ = thread.join();
                    Err(error)
                }
            }
        }
    }
    impl Drop for Listener {
        fn drop(&mut self) {
            unsafe {
                PostThreadMessageW(self.id, WM_QUIT, 0, 0);
            }
            if let Some(thread) = self.thread.take() {
                let _ = thread.join();
            }
        }
    }
    #[test]
    fn hook_thread_survives_posted_messages_and_shuts_down_cleanly() {
        // Passive hook only: no key injection and no real game operations.
        let (listener, _events) = Listener::start().unwrap();
        for _ in 0..3 {
            assert_ne!(unsafe { PostThreadMessageW(listener.id, WM_APP, 0, 0) }, 0);
        }
        std::thread::sleep(std::time::Duration::from_millis(30));
        assert!(!listener.thread.as_ref().unwrap().is_finished());
        drop(listener);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::managers::{
        hotkey_manager::parse_combo,
        shortcuts::{ShortcutAction, ShortcutEvent, ShortcutManager},
    };
    #[test]
    fn windows_media_keys_record_roundtrip_and_trigger_once() {
        for (vk, name) in [
            (0xb0, "MediaNext"),
            (0xb1, "MediaPrevious"),
            (0xb2, "MediaStop"),
            (0xb3, "MediaPlayPause"),
            (0xad, "VolumeMute"),
            (0xae, "VolumeDown"),
            (0xaf, "VolumeUp"),
        ] {
            let raw = windows_key(vk, 0, false).unwrap();
            assert_eq!(raw, RawKey::Named(name));
            assert!(parse_combo(name).is_some());
            let mut manager = ShortcutManager::default();
            manager.start_binding(ShortcutAction::Next, 0).unwrap();
            assert_eq!(
                manager.handle(raw, true, false).1,
                Some(ShortcutEvent::Bound)
            );
            manager.handle(raw, false, false);
            assert_eq!(
                manager.handle(raw, true, false).1,
                Some(ShortcutEvent::Trigger(ShortcutAction::Next))
            );
            assert_eq!(manager.handle(raw, true, false).1, None);
        }
    }
    #[test]
    fn extended_keys_and_shifted_punctuation_have_stable_physical_names() {
        assert_eq!(windows_key(0x0d, 0, true), Some(RawKey::Named("NumEnter")));
        assert_eq!(
            windows_key(0x11, 0, true),
            Some(RawKey::ModRight(Modifier::Ctrl))
        );
        assert_eq!(
            windows_key(0x10, 0x36, false),
            Some(RawKey::ModRight(Modifier::Shift))
        );
        assert_eq!(windows_key(0xbb, 0, false), Some(RawKey::Char('=')));
        assert_eq!(windows_key(0x87, 0, false), Some(RawKey::Named("F24")));
        assert_eq!(windows_key(0xff, 0, false), None);
    }
}
