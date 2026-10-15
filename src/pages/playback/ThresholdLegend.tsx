import { t } from "../../lib/i18n";
export function ThresholdLegend() {
  return (
    <div className="pedal-ai-card__legend">
      <span className="pedal-ai-card__legend-item">
        <span className="pedal-ai-card__legend-swatch pedal-ai-card__legend-swatch--on" />
        {t("按下阈值")}
      </span>
      <span className="pedal-ai-card__legend-item">
        <span className="pedal-ai-card__legend-swatch pedal-ai-card__legend-swatch--off" />
        {t("抬起阈值")}
      </span>
    </div>
  );
}
