import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PerformanceCard } from "./PerformanceCard";
import { DEFAULT_CONFIG, PEDAL_MAPPING } from "./types";
import { setTranslationLanguage } from "../../lib/i18n";

describe("pedal style localized labels", () => {
  it.each(["zh-CN", "en"] as const)(
    "keeps stable backend values in %s",
    (language) => {
      setTranslationLanguage(language);
      const change = vi.fn();
      const { rerender } = render(
        <PerformanceCard
          config={DEFAULT_CONFIG}
          onChange={change}
          onReset={() => {}}
          midiPedalAvailable
        />,
      );
      const select = screen.getByRole("combobox") as HTMLSelectElement;
      for (const value of Object.values(PEDAL_MAPPING)) {
        fireEvent.change(select, { target: { value } });
        expect(change).toHaveBeenLastCalledWith({ pedal_style: value });
        rerender(
          <PerformanceCard
            config={{ ...DEFAULT_CONFIG, pedal_style: value }}
            onChange={change}
            onReset={() => {}}
            midiPedalAvailable
          />,
        );
        expect(select.value).toBe(value);
      }
      setTranslationLanguage("auto");
    },
  );
});
