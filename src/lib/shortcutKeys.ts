/** Physical names match the global Windows listener, independent of Shift/layout. */
export function shortcutCombo(event: Pick<KeyboardEvent,"key"|"code"|"ctrlKey"|"altKey"|"shiftKey"|"metaKey">): string | null {
  const names: Record<string,string> = {
    MediaTrackNext:"MediaNext", MediaNextTrack:"MediaNext", MediaTrackPrevious:"MediaPrevious", MediaPreviousTrack:"MediaPrevious",
    MediaStop:"MediaStop", MediaPlayPause:"MediaPlayPause", AudioVolumeMute:"VolumeMute", AudioVolumeDown:"VolumeDown", AudioVolumeUp:"VolumeUp",
    ArrowUp:"Up",ArrowDown:"Down",ArrowLeft:"Left",ArrowRight:"Right",Space:"Space"," ":"Space",
    Escape:"Escape",Tab:"Tab",Enter:"Enter",Backspace:"Backspace",Delete:"Delete",Insert:"Insert",Home:"Home",End:"End",PageUp:"PageUp",PageDown:"PageDown",
    CapsLock:"CapsLock",NumLock:"NumLock",ScrollLock:"ScrollLock",Pause:"Pause",PrintScreen:"PrintScreen",
    Minus:"-",Equal:"=",BracketLeft:"[",BracketRight:"]",Backslash:"\\",Semicolon:";",Quote:"'",Comma:",",Period:".",Slash:"/",Backquote:"`",
    NumpadDecimal:"NumDecimal",NumpadAdd:"NumAdd",NumpadSubtract:"NumSubtract",NumpadMultiply:"NumMultiply",NumpadDivide:"NumDivide",NumpadEnter:"NumEnter",
  };
  const {key,code}=event;
  if (["Control","Shift","Alt","Meta","AltGraph"].includes(key)) return null;
  let name=names[code] || names[key];
  if (/^Key[A-Z]$/.test(code)) name=code.slice(3);
  else if (/^Digit[0-9]$/.test(code)) name=code.slice(5);
  else if (/^Numpad[0-9]$/.test(code)) name="Num"+code.slice(6);
  else if (/^F([1-9]|1[0-9]|2[0-4])$/.test(key)) name=key;
  else if (!name && /^[a-zA-Z0-9]$/.test(key)) name=key.toUpperCase();
  if (!name) return null;
  return [event.ctrlKey && "Ctrl",event.altKey && "Alt",event.shiftKey && "Shift",event.metaKey && "Cmd",name].filter(Boolean).join("+");
}
