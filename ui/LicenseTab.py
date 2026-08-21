from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QTextEdit)
from PyQt6.QtGui import QFont


_LICENSE_TEXTS: dict[str, str] = {
    "HuMidi": """\
MIT License

Copyright (c) 2026 smyGitt
Modifications Copyright (c) 2026 Xingkong3027

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
""",

    "PedalAI Dataset": """\
The following datasets relate to the planned experimental BiLSTM pedal
feature. HuMidi Xingkong Edition v2.0.0-xk.1 does not bundle or enable
an ONNX pedal model.

────────────────
POP909        
────────────────
A piano MIDI dataset of 909 popular songs with performance annotations.

Citation:
  Wang, Z., Chen, K., Jiang, J., Zhang, Y., Xu, M., Dai, S., Xia, G.,
  & Fazekas, G. (2020). POP909: A Pop-song Dataset for Music Arrangement
  Generation. Proceedings of ISMIR 2020.

License : MIT
URL     : https://github.com/music-x-lab/POP909-Dataset

────────────────
GiantMIDI-Piano
────────────────
A large-scale MIDI dataset of classical piano music transcribed from
audio recordings.

Citation:
  Kong, Q., Li, B., Chen, J., & Wang, Y. (2020). GiantMIDI-Piano: A
  large-scale MIDI dataset for classical piano music. arXiv:2010.07061.

License : Creative Commons Attribution 4.0 International (CC BY 4.0)

  You are free to share and adapt the material for any purpose, provided
  appropriate credit is given.

URL     : https://github.com/bytedance/GiantMIDI-Piano
""",

    "Third-Party Libraries": """\
PyQt6
  License : GPL v3 / Commercial (Riverbank Computing)
  URL     : https://riverbankcomputing.com/software/pyqt/

mido
  License : MIT
  URL     : https://github.com/mido/mido

pynput
  License : LGPL v3
  URL     : https://github.com/moses-palmer/pynput

numpy
  License : BSD 3-Clause
  URL     : https://numpy.org/

PyInstaller
  License : GPL v2-or-later with a bootloader exception
  URL     : https://pyinstaller.org/
""",
}


class LicenseTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QLabel("Licenses & Credits")
        header.setProperty("role", "title")
        layout.addWidget(header)

        selector_row = QHBoxLayout()
        selector_row.setSpacing(8)
        sel_lbl = QLabel("View:")
        sel_lbl.setProperty("role", "muted")
        sel_lbl.setFixedWidth(34)
        self._combo = QComboBox()
        for name in _LICENSE_TEXTS:
            self._combo.addItem(name, name)
        self._combo.currentIndexChanged.connect(self._on_changed)
        selector_row.addWidget(sel_lbl)
        selector_row.addWidget(self._combo, 1)
        layout.addLayout(selector_row)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("Courier New", 9))
        self._text.setPlainText(_LICENSE_TEXTS.get(str(self._combo.currentData()), ""))
        layout.addWidget(self._text)

    def _on_changed(self, _index: int) -> None:
        self._text.setPlainText(_LICENSE_TEXTS.get(str(self._combo.currentData()), ""))

    def retranslate_combo_items(self, tr) -> None:
        current = str(self._combo.currentData() or "HuMidi")
        self._combo.blockSignals(True)
        self._combo.clear()
        for name in _LICENSE_TEXTS:
            self._combo.addItem(tr(name), name)
        self._combo.setCurrentIndex(max(0, self._combo.findData(current)))
        self._combo.blockSignals(False)
        self._on_changed(self._combo.currentIndex())
