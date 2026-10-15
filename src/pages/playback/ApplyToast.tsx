import { t } from "../../lib/i18n";
import { Button } from "../../components/Button";

interface ApplyToastProps {
  visible: boolean;
  onApply: () => void;
  onDiscard: () => void;
  shake?: boolean;
  savingSong?: boolean;
  disabled?: boolean;
}

export function ApplyToast({
  visible,
  onApply,
  onDiscard,
  shake,
  savingSong = false,
  disabled = false,
}: ApplyToastProps) {
  return (
    <div
      className={`apply-toast${visible ? " apply-toast--visible" : ""}${shake ? " apply-toast--shake" : ""}`}
    >
      <span className="apply-toast__msg">
        {t(
          savingSong
            ? "参数已修改，应用后保存此曲目并返回歌单。"
            : "参数已修改，应用后更新当前演奏。",
        )}
      </span>
      <Button variant="accent" disabled={disabled} onClick={onApply}>
        {t("应用修改")}
      </Button>
      <Button disabled={disabled} onClick={onDiscard}>
        {t("放弃修改")}
      </Button>
    </div>
  );
}
