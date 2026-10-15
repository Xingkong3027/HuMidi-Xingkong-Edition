import { beforeEach, expect, it, vi } from "vitest";
const native=vi.hoisted(()=>({open:vi.fn(),save:vi.fn()}));
vi.mock("@tauri-apps/plugin-dialog",()=>native);
import { open, save, isNativeFileDialogOpen, dialogSnapshot } from "./appDialogs";
beforeEach(()=>{vi.clearAllMocks();});
it("delegates MIDI multi-select and filters to the native picker",async()=>{
 native.open.mockResolvedValue(["I:/中文/一.mid","I:/中文/二.midi"]);
 const options={multiple:true,defaultPath:"I:/中文",filters:[{name:"MIDI",extensions:["mid","midi"]}]};
 expect(await open(options)).toEqual(["I:/中文/一.mid","I:/中文/二.midi"]);
 expect(native.open).toHaveBeenCalledWith(options);expect(dialogSnapshot()).toBeNull();expect(isNativeFileDialogOpen()).toBe(false);
});
it("delegates folder selection and preserves cancellation",async()=>{
 native.open.mockResolvedValueOnce("G:/歌曲").mockResolvedValueOnce(null);
 const options={directory:true,multiple:false};expect(await open(options)).toBe("G:/歌曲");expect(native.open).toHaveBeenCalledWith(options);
 expect(await open(options)).toBeNull();
});
it("passes export filename and filters through to Windows save",async()=>{
 native.save.mockResolvedValueOnce("I:/备份/歌单.humidiplaylist").mockResolvedValueOnce(null);
 const options={defaultPath:"歌单.humidiplaylist",filters:[{name:"HuMidi",extensions:["humidiplaylist"]}]};
 expect(await save(options)).toBe("I:/备份/歌单.humidiplaylist");expect(native.save).toHaveBeenCalledWith(options);expect(await save(options)).toBeNull();
});
it("blocks playback while a native chooser is open and resets after errors",async()=>{
 let release!:(path:string)=>void;native.open.mockImplementationOnce(()=>new Promise(resolve=>{release=resolve;}));
 const choosing=open();expect(isNativeFileDialogOpen()).toBe(true);release("I:/one.mid");await choosing;expect(isNativeFileDialogOpen()).toBe(false);
 native.save.mockRejectedValueOnce(new Error("unavailable"));await expect(save()).rejects.toThrow("unavailable");expect(isNativeFileDialogOpen()).toBe(false);
});
