import { open as nativeOpen, save as nativeSave, type OpenDialogOptions, type SaveDialogOptions } from "@tauri-apps/plugin-dialog";

export type DialogRequest = {
  id: number;
  kind: "confirm" | "message" | "prompt" | "color";
  title: string;
  text: string;
  value?: string;
  okLabel?: string;
  cancelLabel?: string;
};
type Answer = string | boolean | null;
let nextId = 0;
let active: DialogRequest | null = null;
const queue: { request: DialogRequest; resolve: (value: Answer) => void }[] = [];
const listeners = new Set<() => void>();
export const subscribeDialogs = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; };
export const dialogSnapshot = () => active;
function notify() { for (const listener of listeners) listener(); }
function requestDialog(request: Omit<DialogRequest, "id">): Promise<Answer> {
  return new Promise((resolve) => {
    queue.push({ request: { ...request, id: ++nextId }, resolve });
    if (!active) { active = queue[0].request; notify(); }
  });
}
export function finishDialog(id: number, answer: Answer) {
  if (active?.id !== id) return;
  const item = queue.shift(); active = queue[0]?.request ?? null;
  item?.resolve(answer); notify();
}
export async function ask(text: string, options: { title?: string; kind?: string; okLabel?: string; cancelLabel?: string } = {}): Promise<boolean> {
  return await requestDialog({ kind:"confirm", title:options.title ?? "确认", text, okLabel:options.okLabel, cancelLabel:options.cancelLabel }) === true;
}
export async function message(text: string, title = "提示"): Promise<void> {
  await requestDialog({kind:"message", title, text});
}
export async function promptText(text: string, value = "", title = "重命名"): Promise<string | null> {
  return await requestDialog({kind:"prompt",title,text,value}) as string | null;
}
// File/folder browsing uses the native OS picker; application messages remain themed.
let nativeDialogDepth = 0;
export const isNativeFileDialogOpen = () => nativeDialogDepth > 0;
export async function open(options: OpenDialogOptions = {}): Promise<string | string[] | null> {
  nativeDialogDepth++;
  try { return await nativeOpen(options); }
  finally { nativeDialogDepth--; }
}
export async function save(options: SaveDialogOptions = {}): Promise<string | null> {
  nativeDialogDepth++;
  try { return await nativeSave(options); }
  finally { nativeDialogDepth--; }
}

export async function chooseColor(value: string): Promise<string | null> {
  return await requestDialog({kind:"color",title:"选择颜色",text:"",value}) as string | null;
}
