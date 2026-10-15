import {act,fireEvent,render,screen,waitFor,cleanup} from "@testing-library/react";
import {afterEach,beforeEach,expect,it,vi} from "vitest";
import {setTranslationLanguage} from "../../lib/i18n";
import {ShortcutSettings} from "./ShortcutSettings";
const mock=vi.hoisted(()=>({invoke:vi.fn(),events:new Map<string,(v:any)=>void>(),startSave:vi.fn()}));
vi.mock("@tauri-apps/api/core",()=>({invoke:mock.invoke}));
vi.mock("../../lib/tauri",()=>({isTauri:()=>true,getHotkeys:()=>Promise.resolve(["F6","Ctrl+S"]),startSaveBinding:mock.startSave,onEvent:(name:string,cb:(v:any)=>void)=>{mock.events.set(name,cb);return Promise.resolve(()=>mock.events.delete(name));}}));
const config=():{version:number;bindings:Record<string,[string|null,string|null]>}=>({version:3,bindings:{play_pause:["F6",null],stop:["F7",null],next:[null,null],previous:[null,null]}});
beforeEach(()=>{setTranslationLanguage("zh-CN");mock.invoke.mockReset();mock.events.clear();mock.startSave.mockReset().mockResolvedValue(undefined);mock.invoke.mockImplementation((cmd:string,args:any)=>{
 if(cmd==="get_shortcuts")return Promise.resolve(config());
 if(cmd==="finish_shortcut_binding"){const c=config();c.bindings.next[0]=args.combo;return Promise.resolve({shortcuts:c,save_label:"Ctrl+S"});}
 return Promise.resolve();
});});
afterEach(()=>{cleanup();setTranslationLanguage("auto");});
const start=async()=>{render(<ShortcutSettings/>);await waitFor(()=>expect(mock.events.size).toBe(3));fireEvent.click(screen.getByRole("button",{name:"下一首快捷键 1"}));await waitFor(()=>expect(mock.invoke).toHaveBeenCalledWith("start_shortcut_binding",{action:"next",slot:0}));};
it("shows navigation actions unbound and captures a combined key without the global hook",async()=>{
 await start();expect(screen.getByRole("button",{name:"上一首快捷键 1"})).toHaveTextContent("未设置");
 fireEvent.keyDown(document,{key:"Control",code:"ControlLeft",ctrlKey:true});
 expect(mock.invoke).not.toHaveBeenCalledWith("finish_shortcut_binding",expect.anything());
 fireEvent.keyDown(document,{key:"k",code:"KeyK",ctrlKey:true});
 await waitFor(()=>expect(mock.invoke).toHaveBeenCalledWith("finish_shortcut_binding",{combo:"Ctrl+K"}));
 expect(await screen.findByRole("button",{name:"下一首快捷键 1"})).toHaveTextContent("Ctrl+K");
});
it("captures a media key once and ignores auto repeat while completion is pending",async()=>{
 await start();fireEvent.keyDown(document,{key:"MediaTrackNext",code:"MediaTrackNext"});fireEvent.keyDown(document,{key:"MediaTrackNext",code:"MediaTrackNext",repeat:true});
 await waitFor(()=>expect(mock.invoke).toHaveBeenCalledWith("finish_shortcut_binding",{combo:"MediaNext"}));
 expect(mock.invoke.mock.calls.filter(([cmd])=>cmd==="finish_shortcut_binding")).toHaveLength(1);
});
it("Escape cancels recording without changing the binding",async()=>{
 await start();fireEvent.keyDown(document,{key:"Escape",code:"Escape"});
 await waitFor(()=>expect(mock.invoke).toHaveBeenCalledWith("cancel_shortcut_binding"));
 expect(screen.getByRole("button",{name:"下一首快捷键 1"})).toHaveTextContent("未设置");
});
it("accepts global-only media capture and releases the recording state",async()=>{
 await start();const c=config();c.bindings.next[0]="MediaNext";
 act(()=>mock.events.get("xk_shortcut_bound")!(c));
 expect(screen.getByRole("button",{name:"下一首快捷键 1"})).toHaveTextContent("MediaNext");
 expect(screen.queryByText("取消录入")).toBeNull();
});
it("reports a failed binding and allows retry instead of staying in recording mode",async()=>{
 await start();mock.invoke.mockImplementation((cmd)=>cmd==="finish_shortcut_binding"?Promise.reject(new Error("conflict")):Promise.resolve());
 fireEvent.keyDown(document,{key:"F10",code:"F10"});expect(await screen.findByRole("alert")).toHaveTextContent("conflict");
 expect(screen.getByRole("button",{name:"下一首快捷键 1"})).not.toBeDisabled();
});
it("records the save shortcut with the same media-capable foreground path",async()=>{
 render(<ShortcutSettings/>);await waitFor(()=>expect(mock.events.size).toBe(3));fireEvent.click(screen.getByText("更改"));
 fireEvent.keyDown(document,{key:"MediaStop",code:"MediaStop"});await waitFor(()=>expect(mock.invoke).toHaveBeenCalledWith("finish_shortcut_binding",{combo:"MediaStop"}));
 expect(mock.startSave).toHaveBeenCalledOnce();
});

it("blocks the foreground action if the global hook finishes recording first",async()=>{
 await start();const c=config();c.bindings.next[0]="Ctrl+K";
 act(()=>mock.events.get("xk_shortcut_bound")!(c));
 const action=vi.fn();window.addEventListener("keydown",action);
 fireEvent.keyDown(document,{key:"k",code:"KeyK",ctrlKey:true});expect(action).not.toHaveBeenCalled();
 fireEvent.keyUp(document,{key:"k",code:"KeyK",ctrlKey:true});fireEvent.keyDown(document,{key:"k",code:"KeyK",ctrlKey:true});expect(action).toHaveBeenCalledOnce();
 window.removeEventListener("keydown",action);
});
