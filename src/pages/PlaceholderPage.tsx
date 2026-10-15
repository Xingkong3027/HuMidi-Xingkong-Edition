import { t, translateNode } from "../lib/i18n";
interface PlaceholderPageProps {
  title: string;
}

export function PlaceholderPage({ title }: PlaceholderPageProps) {
  return (
    <div className="page-placeholder">
      <h1 className="page-placeholder__title">{translateNode(title)}</h1>
      <p className="page-placeholder__hint">{t("Not built yet.")}</p>
    </div>
  );
}
