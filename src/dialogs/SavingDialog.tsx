import { t } from "../lib/i18n";
import { Modal } from "../components/Modal";
import { Spinner } from "../components/Spinner";

const SAVING_DIALOG_WIDTH = 280;
const SAVING_DIALOG_HEIGHT = 160;

export function SavingDialog() {
  return (
    <Modal
      title={t("Saving...")}
      onClose={() => {}}
      hideClose
      width={SAVING_DIALOG_WIDTH}
      height={SAVING_DIALOG_HEIGHT}
    >
      <div className="saving-dialog">
        <Spinner />
      </div>
    </Modal>
  );
}
