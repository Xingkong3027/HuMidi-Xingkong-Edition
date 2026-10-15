import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it } from "vitest";
import { AppDialogHost } from "./AppDialogHost";
import { ask, message, promptText, dialogSnapshot, finishDialog, chooseColor } from "../lib/appDialogs";
import { setTranslationLanguage } from "../lib/i18n";
beforeEach(()=>{ setTranslationLanguage("zh-CN"); });
afterEach(()=>{const active=dialogSnapshot();if(active)act(()=>finishDialog(active.id,null));});
it("queues styled confirmations and resolves cancelled requests without a native dialog",async()=>{
 render(<AppDialogHost/>);let first!:Promise<boolean>,second!:Promise<void>;
 act(()=>{first=ask("删除歌曲？",{title:"删除歌曲",okLabel:"删除"});second=message("已完成");});
 expect(screen.getByRole("dialog",{name:"删除歌曲"})).toBeTruthy();
 fireEvent.click(screen.getByRole("button",{name:"取消"}));expect(await first).toBe(false);
 await screen.findByRole("dialog",{name:"提示"});fireEvent.click(screen.getByRole("button",{name:"确定"}));await second;expect(dialogSnapshot()).toBeNull();
});
it("renames through the themed text prompt",async()=>{
 render(<AppDialogHost/>);let result!:Promise<string|null>;act(()=>{result=promptText("输入名称","Old");});
 fireEvent.change(screen.getByRole("textbox",{name:"重命名"}),{target:{value:"New"}});fireEvent.click(screen.getByRole("button",{name:"确定"}));expect(await result).toBe("New");
});
it("uses the themed color dialog and rejects invalid hex values",async()=>{
 render(<AppDialogHost/>);let result!:Promise<string|null>;act(()=>{result=chooseColor("#123456");});
 const field=screen.getByRole("textbox",{name:"颜色值"});fireEvent.change(field,{target:{value:"bad"}});
 expect(screen.getByRole("button",{name:"确定"})).toBeDisabled();
 fireEvent.change(field,{target:{value:"#abcdef"}});fireEvent.click(screen.getByRole("button",{name:"确定"}));expect(await result).toBe("#abcdef");
});

