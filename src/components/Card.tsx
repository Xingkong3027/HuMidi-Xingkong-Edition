import { translateNode } from "../lib/i18n";
import type { ReactNode } from "react";
import { Label } from "./Label";

interface CardProps {
  title: string;
  titleButtons?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Card({
  title,
  titleButtons,
  footer,
  children,
  className,
}: CardProps) {
  return (
    <div className={`card${className ? ` ${className}` : ""}`}>
      {translateNode(
        title && (
          <div className="card__title-row">
            <Label className="card__title">{translateNode(title)}</Label>
            {translateNode(titleButtons)}
          </div>
        ),
      )}
      <div className="card__body">{translateNode(children)}</div>
      {translateNode(
        footer && <div className="card__footer">{translateNode(footer)}</div>,
      )}
    </div>
  );
}
