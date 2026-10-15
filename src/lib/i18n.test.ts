import { afterEach, describe, expect, it } from "vitest";
import { resolveLanguage, setTranslationLanguage, t } from "./i18n";
afterEach(() => setTranslationLanguage("auto"));
describe("interface languages", () => {
  it("switches existing labels without translating internal values or source text", () => {
    setTranslationLanguage("zh-CN");
    expect(t("Playback")).toBe("演奏");
    expect(t("my song.mid")).toBe("my song.mid");
    setTranslationLanguage("en");
    expect(t("演奏")).toBe("Playback");
    expect(t("single")).toBe("single");
  });
  it("preserves deliberate separator spacing", () => {
    setTranslationLanguage("en");
    expect(t(" s")).toBe(" s");
    expect(resolveLanguage("zh-CN")).toBe("zh-CN");
  });
});
