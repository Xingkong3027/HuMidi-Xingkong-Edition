//! Scoped Windows playback timer tuning; always undone when the player exits.
pub struct PerformanceSession {
    #[cfg(target_os = "windows")]
    timer_enabled: bool,
}

#[cfg(target_os = "windows")]
#[link(name = "winmm")]
extern "system" {
    fn timeBeginPeriod(period: u32) -> u32;
    fn timeEndPeriod(period: u32) -> u32;
}

impl PerformanceSession {
    pub fn new(enabled: bool) -> Self {
        #[cfg(target_os = "windows")]
        {
            Self {
                timer_enabled: enabled && unsafe { timeBeginPeriod(1) } == 0,
            }
        }
        #[cfg(not(target_os = "windows"))]
        {
            let _ = enabled;
            Self {}
        }
    }

    pub fn set_enabled(&mut self, enabled: bool) {
        #[cfg(target_os = "windows")]
        {
            if enabled && !self.timer_enabled {
                self.timer_enabled = unsafe { timeBeginPeriod(1) } == 0;
            } else if !enabled && self.timer_enabled {
                unsafe {
                    timeEndPeriod(1);
                }
                self.timer_enabled = false;
            }
        }
        #[cfg(not(target_os = "windows"))]
        let _ = enabled;
    }
}

impl Drop for PerformanceSession {
    fn drop(&mut self) {
        #[cfg(target_os = "windows")]
        if self.timer_enabled {
            unsafe {
                timeEndPeriod(1);
            }
        }
    }
}
