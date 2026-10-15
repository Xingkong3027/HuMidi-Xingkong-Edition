import { createContext, useContext, type ReactNode } from "react";
import { usePersistedState } from "./usePersistedState";
import { parseOneOf } from "./persistedParsers";
import {
  resolveLanguage,
  setTranslationLanguage,
  type Language,
} from "../lib/i18n";
const Context = createContext({
  language: "auto" as Language,
  resolved: resolveLanguage("auto"),
  setLanguage: (_language: Language) => {},
});
export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = usePersistedState<Language>(
    "ui_language",
    "auto",
    { parse: parseOneOf(["auto", "zh-CN", "en"] as const) },
  );
  setTranslationLanguage(language);
  return (
    <Context.Provider
      value={{ language, resolved: resolveLanguage(language), setLanguage }}
    >
      {children}
    </Context.Provider>
  );
}
export function useLanguage() {
  return useContext(Context);
}
