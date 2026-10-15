import { translateNode } from "../../lib/i18n";
import { Label } from "../../components/Label";
interface PartCardProps {
  title: string;
  meta: string;
  onClick?: () => void;
  clickable?: boolean;
  timeStr?: string;
}

export function PartCard({
  title,
  meta,
  onClick,
  clickable,
  timeStr,
}: PartCardProps) {
  return (
    <div
      className={`part-card${clickable ? " part-card--clickable" : ""}`}
      onClick={onClick}
      role={clickable ? "button" : undefined}
    >
      <Label className="part-card__title">{translateNode(title)}</Label>
      <Label className="part-card__meta">{translateNode(meta)}</Label>
      {translateNode(
        timeStr && (
          <Label className="part-card__meta part-card__time">
            {translateNode(timeStr)}
          </Label>
        ),
      )}
    </div>
  );
}
