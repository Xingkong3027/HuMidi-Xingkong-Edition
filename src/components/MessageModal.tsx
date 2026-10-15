import { translateNode } from "../lib/i18n";
import type { ReactNode } from "react";
import { Modal } from "./Modal";
import type { Icon as PhosphorIcon } from "@phosphor-icons/react";
import { Button, type ButtonSize } from "./Button";

export interface MessageModalButton {
  label: string;
  onClick: () => void;
  variant?: "default" | "accent";
  leadingIcon?: PhosphorIcon;
  trailingIcon?: PhosphorIcon;
  size?: ButtonSize;
  disabled?: boolean;
}

interface MessageModalProps {
  title: string;
  body: ReactNode;
  buttons: MessageModalButton[];
  onClose?: () => void;
  width?: number;
  height?: number;
}

export function MessageModal({
  title,
  body,
  buttons,
  onClose,
  width = 420,
  height = 220,
}: MessageModalProps) {
  return (
    <Modal
      title={title}
      onClose={onClose ?? (() => {})}
      width={width}
      height={height}
      footer={
        <>
          {translateNode(
            buttons.map((b) => (
              <Button
                key={b.label}
                variant={b.variant}
                size={b.size}
                onClick={b.onClick}
                disabled={b.disabled}
              >
                {translateNode(
                  b.leadingIcon && <b.leadingIcon weight="duotone" />,
                )}
                {translateNode(b.label)}
                {translateNode(
                  b.trailingIcon && <b.trailingIcon weight="duotone" />,
                )}
              </Button>
            )),
          )}
        </>
      }
    >
      <p className="message-modal__text">{translateNode(body)}</p>
    </Modal>
  );
}
