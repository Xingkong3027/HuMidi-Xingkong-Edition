import { t } from "../lib/i18n";
import { SpinnerGapIcon } from "@phosphor-icons/react";

export function Spinner() {
  return (
    <span className="spinner" role="status" aria-label={t("Loading")}>
      <SpinnerGapIcon weight="duotone" />
    </span>
  );
}
