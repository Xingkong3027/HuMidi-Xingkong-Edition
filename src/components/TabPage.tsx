import { translateNode } from "../lib/i18n";
import type { ReactNode } from "react";
import { Button } from "./Button";

interface TabPageProps {
  title?: string;
  tabs: readonly string[];
  active: number;
  onChange: (index: number) => void;
  lead?: ReactNode;
  overlay?: ReactNode;
  children: ReactNode;
}

export function TabPage({
  title,
  tabs,
  active,
  onChange,
  lead,
  overlay,
  children,
}: TabPageProps) {
  return (
    <div className="tab-page">
      <div className="tab-page__header">
        {translateNode(
          title && <h1 className="tab-page__title">{translateNode(title)}</h1>,
        )}
        {translateNode(lead)}
        <div className="tab-page__tabs">
          {translateNode(
            tabs.map((label, i) => (
              <Button
                key={label}
                variant="tab"
                active={active === i}
                onClick={() => onChange(i)}
              >
                {translateNode(label)}
              </Button>
            )),
          )}
        </div>
      </div>
      <div className="tab-page__body">
        <div
          className={`tab-page__page${overlay ? " tab-page__page--with-overlay" : ""}`}
        >
          {translateNode(children)}
        </div>
        {translateNode(overlay)}
      </div>
    </div>
  );
}
