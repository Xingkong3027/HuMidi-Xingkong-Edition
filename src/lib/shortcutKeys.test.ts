import { expect,it } from "vitest";
import { shortcutCombo } from "./shortcutKeys";
const key=(key:string,code=key,mods:Partial<KeyboardEvent>={})=>shortcutCombo({key,code,ctrlKey:false,altKey:false,shiftKey:false,metaKey:false,...mods});
it("maps all media and volume keys to the Windows canonical names",()=>{
 for(const [input,output] of [["MediaTrackNext","MediaNext"],["MediaTrackPrevious","MediaPrevious"],["MediaStop","MediaStop"],["MediaPlayPause","MediaPlayPause"],["AudioVolumeMute","VolumeMute"],["AudioVolumeDown","VolumeDown"],["AudioVolumeUp","VolumeUp"]]) expect(key(input)).toBe(output);
 expect(key("Unidentified","MediaTrackNext")).toBe("MediaNext");
});
it("records physical letters, shifted punctuation, numpad and combined modifiers",()=>{
 expect(key("+","Equal",{ctrlKey:true,shiftKey:true})).toBe("Ctrl+Shift+=");
 expect(key("a","KeyA",{altKey:true,metaKey:true})).toBe("Alt+Cmd+A");
 expect(key("1","Numpad1")).toBe("Num1");expect(key("Enter","NumpadEnter")).toBe("NumEnter");
 expect(key("F24")).toBe("F24");expect(key("Control","ControlLeft")).toBeNull();expect(key("Unidentified")).toBeNull();
});
