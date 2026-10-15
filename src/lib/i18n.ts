import type { ReactNode } from "react";
import translations from "./translations.json";
import englishOverrides from "./english-overrides.json";
export type Language = "auto" | "zh-CN" | "en";
const dictionary = translations as Record<string, string>;
const english: Record<string, string> = {
  ...Object.fromEntries(Object.entries(dictionary).map(([en, zh]) => [zh, en])),
  ...englishOverrides,
};
let current: Language = "auto";
export function resolveLanguage(language: Language): "zh-CN" | "en" {
  if (language !== "auto") return language;
  return typeof navigator !== "undefined" &&
    navigator.language.toLowerCase().startsWith("zh")
    ? "zh-CN"
    : "en";
}
export function setTranslationLanguage(language: Language) {
  current = language;
}
/** Unknown text (song names, paths and original license texts) is preserved. */
export function t(text: string): string {
  const normalized = text.trim().replace(/\s+/g, " ");
  const source = resolveLanguage(current) === "zh-CN" ? dictionary : english;
  if (source[normalized]) return text.replace(text.trim(), source[normalized]);
  return text;
}
export function translateNode(node: ReactNode): ReactNode {
  if (typeof node === "string") return t(node);
  if (Array.isArray(node)) return node.map(translateNode);
  return node;
}
