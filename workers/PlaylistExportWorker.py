from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal as Signal


class PlaylistExportWorker(QObject):
    progress = Signal(int, int, str)
    succeeded = Signal(int, str)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, playlist_manager, destination: str, complete: bool):
        super().__init__()
        self.playlist_manager = playlist_manager
        self.destination = destination
        self.complete = complete

    def run(self):
        try:
            count = self.playlist_manager.export_playlist(
                self.destination,
                complete=self.complete,
                progress_callback=lambda current, total, name: self.progress.emit(
                    int(current), int(total), str(name)
                ),
            )
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(count, self.destination)
        finally:
            self.finished.emit()
