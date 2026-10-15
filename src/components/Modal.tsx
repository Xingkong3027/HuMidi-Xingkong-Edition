import { t, translateNode } from "../lib/i18n";
import { useEffect, useId, useRef, type ReactNode } from "react";
import { Button } from "./Button";

interface ModalProps {
  title: string;
  onClose: () => void;
  hideClose?: boolean;
  footer?: ReactNode;
  width?: number;
  height?: number;
  children: ReactNode;
}

export function Modal({
  title,
  onClose,
  hideClose,
  footer,
  width = 600,
  height = 400,
  children,
}: ModalProps) {
  const titleId = useId();
  const panel = useRef<HTMLDivElement>(null);
  const close = useRef(onClose); close.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    if (!panel.current?.contains(document.activeElement)) panel.current?.querySelector<HTMLElement>("button:not(:disabled), input:not(:disabled), [tabindex]")?.focus();
    const keydown = (event: KeyboardEvent) => {
      const dialogs = document.querySelectorAll('[role="dialog"]');
      if (dialogs[dialogs.length-1] !== panel.current) return;
      if (event.key === "Escape" && !hideClose) { event.preventDefault(); event.stopPropagation(); close.current(); }
      if (event.key === "Tab") {
        const elements = Array.from(panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]') ?? []).filter(e=>e.getClientRects().length>0);
        const first=elements[0], last=elements[elements.length-1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    document.addEventListener("keydown",keydown,true);
    return () => { document.removeEventListener("keydown",keydown,true); if(previous?.isConnected)previous.focus(); };
  }, [hideClose]);
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="modal"
        style={{ width, height }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal__title-row">
          <span id={titleId} className="modal__title">{translateNode(title)}</span>
          {translateNode(
            !hideClose && (
              <Button variant="icon" subtle onClick={onClose} aria-label={t("关闭弹窗")}>
                {t("×")}
              </Button>
            ),
          )}
        </div>
        <div className="modal__body">{translateNode(children)}</div>
        {translateNode(
          footer && (
            <div className="modal__footer">{translateNode(footer)}</div>
          ),
        )}
      </div>
    </div>
  );
}
