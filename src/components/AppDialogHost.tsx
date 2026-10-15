import { useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { dialogSnapshot, finishDialog, subscribeDialogs, type DialogRequest } from "../lib/appDialogs";
import { Modal } from "./Modal";
import { Button } from "./Button";
import { t } from "../lib/i18n";
import { ColorPickerDialog } from "../dialogs/ColorPickerDialog";

function TextDialog({ request }: { request: DialogRequest }) {
  const [value, setValue] = useState(request.value ?? "");
  const cancel = () => finishDialog(request.id, request.kind === "confirm" ? false : null);
  const accept = () => finishDialog(request.id, request.kind === "prompt" ? value : true);
  return <Modal title={t(request.title)} onClose={cancel} width={520} height={request.kind === "prompt" ? 260 : 240}
    footer={<>
      {request.kind !== "message" && <Button onClick={cancel}>{t(request.cancelLabel ?? "取消")}</Button>}
      <Button variant="accent" onClick={accept}>{t(request.okLabel ?? "确定")}</Button>
    </>}>
    <p className="message-modal__text">{t(request.text)}</p>
    {request.kind === "prompt" && <form onSubmit={(e) => { e.preventDefault(); accept(); }}>
      <input className="field app-dialog__input" aria-label={t(request.title)} value={value} onChange={(e) => setValue(e.target.value)} autoFocus />
    </form>}
  </Modal>;
}
export function AppDialogHost() {
  const request = useSyncExternalStore(subscribeDialogs, dialogSnapshot);
  if (!request) return null;
  return createPortal(<div className="app-dialog-host">
    {request.kind === "color" ? <ColorPickerDialog key={request.id} request={request} />
      : <TextDialog key={request.id} request={request} />}
  </div>, document.body);
}
