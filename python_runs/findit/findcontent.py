#!/usr/bin/env python3
import os
import sys
import traceback
from typing import *
from dataclasses import dataclass
# e.g., if finder code is at project_root/tools/find_tools.py
sys.path.append("/path/to/project_root")
from abstract_paths import findContent, findContentAndEdit, getLineNums, get_line_content

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QTextEdit, QListWidget, QListWidgetItem,
    QCheckBox, QFileDialog, QSpinBox, QMessageBox
)


# your code: the functions you pasted
from abstract_paths import (   # <- change to your package path
    findContent, findContentAndEdit, getLineNums, get_line_content
)

# Data structures

@dataclass
class SearchParams:
    directory: str
    paths: Union[bool, str] = True
    exts: Union[bool, str, List[str]] = True
    recursive: bool = True
    strings: List[str] = None
    total_strings: bool = False
    parse_lines: bool = False
    spec_line: Union[bool, int] = False
    get_lines: bool = True


# ————————————————————————————————————————————————————————————————
# Background worker so the UI doesn’t freeze
class SearchWorker(QThread):
    log = pyqtSignal(str)
    done = pyqtSignal(list)

    def __init__(self, params: SearchParams):
        super().__init__()
        self.params = params

    def run(self):
        try:
            if findContent is None:
                raise RuntimeError(
                    "Could not import your finder functions. Import error:\n"
                    f"{_IMPORT_ERR if '_IMPORT_ERR' in globals() else 'unknown'}"
                )
            self.log.emit("🔎 Searching…\n")
            results = findContent(
                directory=self.params.directory,
                paths=self.params.paths,
                exts=self.params.exts,
                recursive=self.params.recursive,
                strings=self.params.strings or [],
                total_strings=self.params.total_strings,
                parse_lines=self.params.parse_lines,
                spec_line=self.params.spec_line,
                get_lines=self.params.get_lines
            )
            self.done.emit(results)
        except Exception:
            self.log.emit(traceback.format_exc())
            self.done.emit([])


# ————————————————————————————————————————————————————————————————
# Main GUI
class FinderTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())
        grid = QGridLayout()

        # Directory picker
        self.dir_in = QLineEdit(os.getcwd())
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self.browse_dir)

        # Strings to find (comma-separated)
        self.strings_in = QLineEdit("")
        self.strings_in.setPlaceholderText("comma,separated,strings")

        # Extensions (comma-separated or regex pipe: ts,tsx,js,jsx or ts|tsx|js|jsx)
        self.exts_in = QLineEdit("ts,tsx,js,jsx,css")
        self.exts_in.setPlaceholderText("ts,tsx,js,jsx,css")

        # Optional: restrict to a sub-path (regex or boolean True)
        self.paths_in = QLineEdit("")
        self.paths_in.setPlaceholderText("True (all) or regex like ^src/")

        # Flags
        self.chk_recursive = QCheckBox("Recursive"); self.chk_recursive.setChecked(True)
        self.chk_total = QCheckBox("Require ALL strings (total_strings)"); self.chk_total.setChecked(False)
        self.chk_parse = QCheckBox("parse_lines"); self.chk_parse.setChecked(False)
        self.chk_getlines = QCheckBox("get_lines"); self.chk_getlines.setChecked(True)

        # Spec line (0 = off). Your code uses False to mean “disabled”, so we map 0→False.
        self.spec_spin = QSpinBox(); self.spec_spin.setRange(0, 999999)
        self.spec_spin.setValue(0)
        self.spec_spin.setToolTip("0 disables spec_line. >0 checks only that line (1-based).")

        # Run + Open in editor
        self.btn_run = QPushButton("Run search")
        self.btn_run.clicked.connect(self.start_search)

        self.btn_open_all = QPushButton("Open all hits in VS Code")
        self.btn_open_all.clicked.connect(self.open_all_hits)
        self.btn_open_all.setEnabled(False)

        # Layout form
        r = 0
        grid.addWidget(QLabel("Directory"), r, 0); grid.addWidget(self.dir_in, r, 1); grid.addWidget(btn_browse, r, 2); r+=1
        grid.addWidget(QLabel("Strings"),   r, 0); grid.addWidget(self.strings_in, r, 1, 1, 2); r+=1
        grid.addWidget(QLabel("Extensions"),r, 0); grid.addWidget(self.exts_in, r, 1, 1, 2); r+=1
        grid.addWidget(QLabel("Paths"),     r, 0); grid.addWidget(self.paths_in, r, 1, 1, 2); r+=1

        flag_row = QHBoxLayout()
        for w in (self.chk_recursive, self.chk_total, self.chk_parse, self.chk_getlines):
            flag_row.addWidget(w)
        grid.addLayout(flag_row, r, 0, 1, 3); r+=1

        sp = QHBoxLayout()
        sp.addWidget(QLabel("spec_line (0=off):"))
        sp.addWidget(self.spec_spin)
        sp.addStretch(1)
        grid.addLayout(sp, r, 0, 1, 3); r+=1

        self.layout().addLayout(grid)

        cta = QHBoxLayout()
        cta.addWidget(self.btn_run)
        cta.addStretch(1)
        cta.addWidget(self.btn_open_all)
        self.layout().addLayout(cta)

        # Output area
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setLineWrapMode(QTextEdit.NoWrap)
        self.layout().addWidget(QLabel("Results"))
        self.layout().addWidget(self.log, stretch=2)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self.open_one)
        self.layout().addWidget(self.list, stretch=3)

        self._last_results = []

    # — UI helpers —
    def browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Choose directory", self.dir_in.text() or os.getcwd())
        if d:
            self.dir_in.setText(d)

    def make_params(self) -> SearchParams:
        directory = self.dir_in.text().strip()
        if not directory or not os.path.isdir(directory):
            raise ValueError("Directory is missing or not a valid folder.")

        # strings
        s_raw = [s.strip() for s in self.strings_in.text().split(",") if s.strip()]
        # exts: allow "ts,tsx" or "ts|tsx"
        e_raw = self.exts_in.text().strip()
        exts: Union[bool, str, List[str]] = True
        if e_raw:
            if "|" in e_raw:
                exts = e_raw
            else:
                exts = [e.strip() for e in e_raw.split(",") if e.strip()]

        # paths
        p_raw = self.paths_in.text().strip()
        paths: Union[bool, str] = True if not p_raw else p_raw

        spec_line = self.spec_spin.value()
        spec_line = False if spec_line == 0 else int(spec_line)

        return SearchParams(
            directory=directory,
            paths=paths,
            exts=exts,
            recursive=self.chk_recursive.isChecked(),
            strings=s_raw,
            total_strings=self.chk_total.isChecked(),
            parse_lines=self.chk_parse.isChecked(),
            spec_line=spec_line,
            get_lines=self.chk_getlines.isChecked(),
        )

    # — Actions —
    def start_search(self):
        self.list.clear()
        self.log.clear()
        self.btn_run.setEnabled(False)
        try:
            params = self.make_params()
        except Exception as e:
            QMessageBox.critical(self, "Bad input", str(e))
            self.btn_run.setEnabled(True)
            return

        self.worker = SearchWorker(params)
        self.worker.log.connect(self.append_log)
        self.worker.done.connect(self.populate_results)
        self.worker.finished.connect(lambda: self.btn_run.setEnabled(True))
        self.worker.start()

    def append_log(self, text: str):
        self.log.moveCursor(self.log.textCursor().End)
        self.log.insertPlainText(text)

    def populate_results(self, results: list):
        self._last_results = results or []
        if not results:
            self.append_log("✅ No matches found.\n")
            self.btn_open_all.setEnabled(False)
            return

        self.append_log(f"✅ Found {len(results)} file(s).\n")
        self.btn_open_all.setEnabled(True)

        for fp in results:
            file_path, lines = getLineNums(fp) if getLineNums else (fp, [])
            if not isinstance(file_path, str):
                continue

            if lines:
                for obj in lines:
                    line, content = get_line_content(obj) if get_line_content else (obj.get('line'), obj.get('content'))
                    text = f"{file_path}:{line}"
                    QListWidgetItem(text, self.list)
                    self.append_log(text + "\n")
            else:
                QListWidgetItem(file_path, self.list)
                self.append_log(file_path + "\n")

    def open_one(self, item: QListWidgetItem):
        info = item.text()
        # VS Code: code -g file:line[:col]
        os.system(f'code -g "{info}"')

    def open_all_hits(self):
        for i in range(self.list.count()):
            self.open_one(self.list.item(i))


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔎 React Finder — coherent GUI")
        self.resize(1000, 700)
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        self.finder = FinderTab()
        tabs.addTab(self.finder, "Find Content")
        layout.addWidget(tabs)


def main():
    if any(v is None for v in (findContent, findContentAndEdit, getLineNums, get_line_content)):
        QMessageBox.critical(None, "Import error",
                             "Your finder utilities failed to import.\n\n"
                             "Adjust the import path near the top of this file "
                             "so it points at your module.")
        return 1
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print(traceback.format_exc())
        sys.exit(1)
