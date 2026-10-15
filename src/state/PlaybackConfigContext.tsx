import { translateNode } from "../lib/i18n";
import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { DEFAULT_CONFIG, type PlaybackConfig } from "../pages/playback/types";
import {
  configFromSaved,
  configToPatch,
} from "../pages/playback/persistedConfig";
import { usePersistedPatch } from "./usePersistedState";
import { updatePerformanceConfig } from "../pages/playback/humanization";

interface PlaybackConfigContextValue {
  config: PlaybackConfig;
  defaultConfig: PlaybackConfig;
  editorScope: "defaults" | "song" | "import";
  beginEdit: (settings: PlaybackConfig, scope: "song" | "import") => void;
  endEdit: () => void;
  setConfig: (
    updater: PlaybackConfig | ((c: PlaybackConfig) => PlaybackConfig),
  ) => void;
  updateConfig: (patch: Partial<PlaybackConfig>) => void;
}

const PlaybackConfigContext = createContext<PlaybackConfigContextValue | null>(
  null,
);

export function PlaybackConfigProvider({ children }: { children: ReactNode }) {
  const [defaultConfig, setDefaults] = usePersistedPatch<PlaybackConfig>(
    "playback settings",
    DEFAULT_CONFIG,
    {
      fromConfig: (saved) => configFromSaved({ ...saved, ...((saved.xk_default_settings as object) ?? {}) }),
      toPatch: (value) => ({ ...configToPatch(value), xk_default_settings: configToPatch(value) }),
    },
  );

  const [editor, setEditor] = useState<PlaybackConfig | null>(null);
  const [editorScope, setScope] = useState<"defaults" | "song" | "import">("defaults");
  const config = editor ?? defaultConfig;
  const value = useMemo(
    () => ({
      config,
      defaultConfig,
      editorScope,
      beginEdit: (settings: PlaybackConfig, scope: "song" | "import") => { setEditor(settings); setScope(scope); },
      endEdit: () => { setEditor(null); setScope("defaults"); },
      // Restoring a song and generating its curves must never overwrite import defaults.
      setConfig: (updater: PlaybackConfig | ((c: PlaybackConfig) => PlaybackConfig)) => {
        setEditor((c) => typeof updater === "function" ? updater(c ?? defaultConfig) : updater);
      },
      updateConfig: (patch: Partial<PlaybackConfig>) => editor !== null
        ? setEditor((c) => updatePerformanceConfig(c ?? defaultConfig, patch))
        : setDefaults((c) => updatePerformanceConfig(c, patch)),
    }),
    [config, defaultConfig, editor, editorScope, setDefaults],
  );

  return (
    <PlaybackConfigContext.Provider value={value}>
      {translateNode(children)}
    </PlaybackConfigContext.Provider>
  );
}

export function usePlaybackConfig() {
  const ctx = useContext(PlaybackConfigContext);
  if (!ctx)
    throw new Error(
      "usePlaybackConfig must be used within PlaybackConfigProvider",
    );
  return ctx;
}
