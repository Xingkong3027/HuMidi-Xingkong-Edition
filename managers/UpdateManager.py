import json
import os
import platform
import subprocess
import sys
import urllib.request

from PyQt6.QtCore import QThread, pyqtSignal

RELEASES_API = "https://api.github.com/repos/smyGitt/HuMidi-Roblox-Piano-Autoplayer/releases/latest"


def parse_version(tag: str) -> tuple:
    try:
        return tuple(int(x) for x in tag.lstrip("v").strip().split("."))
    except (ValueError, AttributeError):
        return ()


def _get_platform_asset(assets: list) -> str:
    system = platform.system()
    for asset in assets:
        name = asset.get("name", "").lower()
        if system == "Windows" and name == "humidi.exe":
            return asset["browser_download_url"]
        if system == "Darwin" and name == "humidi.tar.gz":
            return asset["browser_download_url"]
    return ""


class UpdateChecker(QThread):
    update_available = pyqtSignal(str, str)  # (latest_tag, download_url)
    no_update        = pyqtSignal()
    check_failed     = pyqtSignal()

    def __init__(self, current_version: str, force: bool = False):
        super().__init__()
        self._current_version = current_version
        self._force = force

    def run(self):
        if not self._force and not getattr(sys, "frozen", False):
            return
        try:
            req = urllib.request.Request(
                RELEASES_API, headers={"User-Agent": "HuMidi-updater"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())

            latest_tag = data.get("tag_name", "")
            if not latest_tag:
                return

            latest_tuple = parse_version(latest_tag)
            current_tuple = parse_version(self._current_version)
            if not latest_tuple or not current_tuple:
                return

            if latest_tuple <= current_tuple:
                self.no_update.emit()
                return

            download_url = _get_platform_asset(data.get("assets", []))
            if not download_url:
                return

            self.update_available.emit(latest_tag, download_url)
        except Exception:
            self.check_failed.emit()


class DownloadWorker(QThread):
    finished = pyqtSignal(str)  # tmp file path
    failed = pyqtSignal(str)    # error message

    def __init__(self, download_url: str):
        super().__init__()
        self._url = download_url

    def run(self):
        system = platform.system()
        exe_dir = os.path.dirname(sys.executable)
        ext = ".tar.gz" if system == "Darwin" else ".exe"
        tmp_path = os.path.join(exe_dir, f"_humidi_update_tmp{ext}")
        try:
            req = urllib.request.Request(
                self._url, headers={"User-Agent": "HuMidi-updater"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                with open(tmp_path, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)

            self._launch_replace_script(tmp_path)
            self.finished.emit(tmp_path)
        except Exception as e:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            self.failed.emit(str(e))

    def _launch_replace_script(self, tmp_path: str):
        current_exe = sys.executable
        exe_dir = os.path.dirname(current_exe)
        system = platform.system()

        if system == "Windows":
            bat_path = os.path.join(exe_dir, "_humidi_updater.bat")
            bat_content = (
                "@echo off\n"
                ":waitloop\n"
                "ping -n 3 127.0.0.1 >nul 2>&1\n"
                f'if exist "{current_exe}" (\n'
                f'    del /f /q "{current_exe}" >nul 2>&1\n'
                f'    if exist "{current_exe}" goto waitloop\n'
                ")\n"
                f'move /y "{tmp_path}" "{current_exe}"\n'
                f'start "" "{current_exe}"\n'
                'del "%~f0"\n'
            )
            with open(bat_path, "w") as f:
                f.write(bat_content)
            subprocess.Popen(
                ["cmd.exe", "/c", bat_path],
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                close_fds=True,
            )

        elif system == "Darwin":
            sh_path = os.path.join(exe_dir, "_humidi_updater.sh")
            sh_content = (
                "#!/bin/bash\n"
                "sleep 2\n"
                f'tar -xzf "{tmp_path}" -C "{exe_dir}"\n'
                f'chmod +x "{current_exe}"\n'
                f'rm -f "{tmp_path}"\n'
                f'open "{current_exe}"\n'
                'rm -- "$0"\n'
            )
            with open(sh_path, "w") as f:
                f.write(sh_content)
            os.chmod(sh_path, 0o755)
            subprocess.Popen(
                ["/bin/bash", sh_path],
                start_new_session=True,
                close_fds=True,
            )
