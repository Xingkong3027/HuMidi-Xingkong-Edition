import { useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { forwardKey, getHotkeys, isTauri, onEvent } from "./tauri";
import { shortcutCombo } from "./shortcutKeys";

export function useKeyForwarding(): void {
  useEffect(() => {
    if (!isTauri()) return;
    let bound = new Set(["F6", "F7", "Ctrl+S"]), save = "Ctrl+S", alive = true;
    const setBindings = (value: { bindings: Record<string, (string | null)[]> }) => { bound = new Set(Object.values(value.bindings).flat().filter((v): v is string => !!v)); bound.add(save); };
    void invoke<{bindings: Record<string,(string|null)[]>}>("get_shortcuts").then(v => { if (alive) setBindings(v); }).catch(() => {});
    void getHotkeys().then(([, label]) => { if (alive) { bound.delete(save); save = label; bound.add(save); } }).catch(() => {});
    const listeners = [onEvent("xk_shortcut_bound", setBindings), onEvent("hotkey_bound_save_updated", label => { bound.delete(save); save = label; bound.add(save); })];
    const send = (event: KeyboardEvent, pressed: boolean) => {
      if (pressed && event.repeat) return;
      if (pressed && bound.has(shortcutCombo(event) ?? "")) event.preventDefault();
      void forwardKey(event.code || event.key, pressed).catch(() => {});
    };
    const down = (e: KeyboardEvent) => send(e, true), up = (e: KeyboardEvent) => send(e, false);
    document.addEventListener("keydown", down);
    document.addEventListener("keyup", up);
    return () => { alive = false; document.removeEventListener("keydown", down); document.removeEventListener("keyup", up); listeners.forEach(p => { void p.then(f => f()); }); };
  }, []);
}
