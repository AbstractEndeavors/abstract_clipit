#!/usr/bin/env python3
import os
import re
import subprocess
import sys
import traceback

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QListWidget, QListWidgetItem, QMessageBox
)

# ——————————————————————————————————————————————————————————————————————
# Remote command for TypeScript check and build
COMMAND = """
echo -e "\n🔧 TypeScript type check starting...\n"
npx tsc --noEmit 2>&1 | tee tsc.log
CI=true yarn build 2>&1 | tee build.log
"""
ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')
# Capture file path and location: file.ext(line,col)
FILE_REGEX = re.compile(r'([^\s:()]+\.(?:ts|tsx|js|jsx))\((\d+),(\d+)\)')
# Regex to grep for erroneous 'use' import from React
GREP_REGEX = r"import\s+[^;]*\buse[^;]*from\s+['\"]react['\"]"

# Safe file read
def read_file(path):
    try:
        with open(path, encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        print(f"❌ Failed to read file {path}: {e}")
        return ""

# Strip ANSI escapes
def strip_ansi(text: str) -> str:
    try:
        return ANSI_RE.sub('', text)
    except Exception as e:
        print(f"❌ Failed to strip ANSI: {e}")
        return text

# Parse explicit error entries: file(line,col)
def get_error_entries(log_text: str, project_path: str):
    entries = []
    for match in FILE_REGEX.finditer(log_text):
        rel, line, col = match.groups()
        full = rel if os.path.isabs(rel) else os.path.normpath(os.path.join(project_path, rel))
        entries.append((full, int(line), int(col)))
    return entries

# Perform a grep fallback for 'use' import in user code
def grep_use_imports(project_path: str):
    results = []
    try:
        proc = subprocess.run(
            ["grep", "-RnE", GREP_REGEX, project_path],
            capture_output=True, text=True, shell=False
        )
        for line in proc.stdout.splitlines():
            parts = line.split("#DELIM#", 1)
        # Using custom delimiter is tricky; simpler: split on :, up to 2 splits
        for ln in proc.stdout.splitlines():
            file, lineno, text = ln.split(':', 2)
            results.append((file, int(lineno), 1))
    except Exception as e:
        print(f"❌ grep_use_imports error: {e}")
    return results

# Run SSH command safely
def run_ssh_cmd(user: str, cmd: str, path: str) -> str:
    try:
        full = f"ssh {user} 'cd {path} && {cmd}'"
        proc = subprocess.run(full, shell=True, capture_output=True, text=True)
        return proc.stdout + proc.stderr
    except Exception as e:
        print(f"❌ run_ssh_cmd error: {e}")
        return ""

# Background worker thread
class Worker(QThread):
    log_line = pyqtSignal(str)
    entries_found = pyqtSignal(list)  # list of (path,line,col)

    def __init__(self, user, project_path):
        super().__init__()
        self.user = user
        self.project_path = project_path

    def run(self):
        tsc_log = os.path.join(self.project_path, 'tsc.log')
        build_log = os.path.join(self.project_path, 'build.log')
        try:
            # Run remote build
            self.log_line.emit(f">>> SSH → {self.user}@…\n")
            output = run_ssh_cmd(self.user, COMMAND, self.project_path)
            # Emit raw output
            for line in output.splitlines():
                self.log_line.emit(line + "\n")

            # Wait for logs
            retries = 0
            while not (os.path.exists(tsc_log) and os.path.exists(build_log)):
                self.msleep(200)
                retries += 1
                if retries > 300:
                    raise TimeoutError("Timed out waiting for log files.")

            # Read and clean logs
            text_tsc = strip_ansi(read_file(tsc_log))
            text_build = strip_ansi(read_file(build_log))
            combined = text_tsc + "\n" + text_build

            # Display build log
            self.log_line.emit("\n── Build Log ──\n")
            for line in text_build.splitlines():
                self.log_line.emit(line + "\n")

            # Explicit error entries
            entries = get_error_entries(combined, self.project_path)
            # Filter to src folder
            src_prefix = os.path.normpath(os.path.join(self.project_path, 'src'))
            user_entries = [e for e in entries if e[0].startswith(src_prefix)]

            # If no explicit entries, try CRA bundler declarations
            if not user_entries:
                for ln in text_build.splitlines():
                    m = re.match(r"^\s*(?:\.?/)?(src/[^\s]+\.(?:ts|tsx|js|jsx))$", ln)
                    if m:
                        full = os.path.normpath(os.path.join(self.project_path, m.group(1)))
                        user_entries.append((full, 1, 1))
                if user_entries:
                    self.log_line.emit("\nℹ️ Bundler-declared file errors:\n")
                    for path,_,_ in user_entries:
                        self.log_line.emit(path + "\n")

            # Grep fallback for 'use' import errors
            if not user_entries and 'use' in combined:
                grep_results = grep_use_imports(self.project_path)
                if grep_results:
                    self.log_line.emit("\n🔍 Found 'use' imports via grep fallback:\n")
                    for path, line, col in grep_results:
                        self.log_line.emit(f"{path}:{line}\n")
                    user_entries = grep_results

            self.entries_found.emit(user_entries)

        except Exception:
            tb = traceback.format_exc()
            self.log_line.emit(f"\n❌ Exception in Worker:\n{tb}\n")
            self.entries_found.emit([])
        finally:
            # Cleanup
            for logf in (tsc_log, build_log):
                try:
                    if os.path.exists(logf): os.remove(logf)
                except Exception:
                    pass

# Main application window
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔍 runFindit GUI")
        self.resize(800, 600)

        # Inputs
        self.user_in = QLineEdit(os.getlogin())
        self.user_in.setPlaceholderText("SSH user")
        self.path_in = QLineEdit(os.getcwd())
        self.path_in.setPlaceholderText("Project path")

        # Run button
        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self.start_work)

        # Log pane
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QTextEdit.NoWrap)

        # Entries list
        self.entry_list = QListWidget()
        self.entry_list.itemClicked.connect(self.open_in_editor)

        # Layout
        top = QHBoxLayout()
        top.addWidget(QLabel("User:")); top.addWidget(self.user_in)
        top.addWidget(QLabel("Path:")); top.addWidget(self.path_in)
        top.addWidget(self.run_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(QLabel("Log Output:"))
        layout.addWidget(self.log_view, stretch=3)
        layout.addWidget(QLabel("Errors (file:line:col):"))
        layout.addWidget(self.entry_list, stretch=1)

    def start_work(self):
        self.run_btn.setEnabled(False)
        self.log_view.clear()
        self.entry_list.clear()
        user = self.user_in.text().strip()
        path = self.path_in.text().strip()
        if not user or not os.path.isdir(path):
            QMessageBox.critical(self, "Error", "Invalid user or project path.")
            self.run_btn.setEnabled(True)
            return
        self.worker = Worker(user, path)
        self.worker.log_line.connect(self.append_log)
        self.worker.entries_found.connect(self.show_entries)
        self.worker.finished.connect(lambda: self.run_btn.setEnabled(True))
        self.worker.start()

    def append_log(self, text):
        try:
            cursor = self.log_view.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_view.setTextCursor(cursor)
            self.log_view.insertPlainText(text)
        except Exception as e:
            print(f"append_log error: {e}")

    def show_entries(self, entries):
        if not entries:
            self.append_log("\n✅ No matching errors found.\n")
            return
        self.append_log("\nErrors found:\n")
        for path, line, col in entries:
            info = f"{path}:{line}:{col}" if col else f"{path}:{line}"
            self.append_log(info + "\n")
            item = QListWidgetItem(info)
            self.entry_list.addItem(item)
            try:
                os.system(f"code -g \"{info}\"")
            except Exception as e:
                self.append_log(f"Failed to open {info}: {e}\n")

    def open_in_editor(self, item):
        try:
            os.system(f"code -g \"{item.text()}\"")
        except Exception as e:
            self.append_log(f"open_in_editor error: {e}\n")

# Entry point
if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception:
        print(traceback.format_exc())
