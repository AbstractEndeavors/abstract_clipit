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
from abstract_utilities import *
logger = get_logFile(__name__)
def save_logs(tsc_log,build_log,project_path):
    try:
        log_dir = os.path.join(project_path,'logs')
        os.makedirs(log_dir,exist_ok=True)
        tsc_data = read_from_file(tsc_log)
        tsc_log_path = os.path.join(log_dir,'tsc.log')
        write_to_file(contents=tsc_data,file_path=tsc_log_path)
        build_data = read_from_file(build_log)
        build_log_path = os.path.join(log_dir,'build.log')
        write_to_file(contents=build_data,file_path=build_log_path)
    except Exception as e:
        print(f"❌ save_logs error: {e}")
        return ""
# ——————————————————————————————————————————————————————————————————————
# Remote command for TypeScript check and build
COMMAND = r"""
set -e
echo "__TSC_BEGIN__"
npx tsc --noEmit || true
echo "__TSC_END__"
echo "__BUILD_BEGIN__"
CI=true yarn build || true
echo "__BUILD_END__"
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
            ["grep", "-RnE", GREP_REGEX, "src"],
            cwd=project_path,
            capture_output=True, text=True
        )
        for ln in proc.stdout.splitlines():
            # format: path:lineno:content
            try:
                file, lineno, _ = ln.split(':', 2)
                results.append((os.path.join(project_path, file), int(lineno), 1))
            except Exception:
                continue
    except Exception as e:
        print(f"❌ grep_use_imports error: {e}")
    return results

# Run SSH command safely
def run_ssh_cmd(user: str, cmd: str, path: str) -> str:
    try:
        # quote path and command safely
        full = f"ssh {user} 'cd {path} && bash -lc {sh_quote(cmd)}'"
        proc = subprocess.run(full, shell=True, capture_output=True, text=True)
        return proc.stdout + proc.stderr
    except Exception as e:
        print(f"❌ run_ssh_cmd error: {e}")
        return ""

    
def run_local_cmd(cmd: str, path: str) -> str:
    try:
        proc = subprocess.run(["bash", "-lc", cmd], cwd=path, capture_output=True, text=True)
        return proc.stdout + proc.stderr
    except Exception as e:
        print(f"❌ run_local_cmd error: {e}")
        return ""
def sh_quote(s: str) -> str:
    # minimal safe quoting
    return "'" + s.replace("'", "'\\''") + "'"
# Background worker thread
def split_sections(raw: str):
    tsc = ""
    build = ""
    # strip ANSI early
    raw = strip_ansi(raw)
    # split by markers
    # anything between __TSC_BEGIN__ and __TSC_END__ is tsc
    # anything between __BUILD_BEGIN__ and __BUILD_END__ is build
    try:
        tsc = raw.split("__TSC_BEGIN__", 1)[1].split("__TSC_END__", 1)[0]
    except Exception:
        pass
    try:
        build = raw.split("__BUILD_BEGIN__", 1)[1].split("__BUILD_END__", 1)[0]
    except Exception:
        pass
    return tsc.strip(), build.strip()
class Worker(QThread):
    log_line = pyqtSignal(str)
    entries_found = pyqtSignal(list)  # list of (path,line,col)



    def __init__(self, user: str, project_path: str, auto_install: bool = False):
        super().__init__()
        self.user = user.strip()  # empty => local mode
        self.project_path = project_path
        self.auto_install = auto_install
        self.module_list = []

    def run(self):
        try:
            # run command
            self.log_line.emit(f">>> Running {'SSH' if self.user else 'local'} build…\n")
            output = (run_ssh_cmd(self.user, COMMAND, self.project_path)
                      if self.user else
                      run_local_cmd(COMMAND, self.project_path))
            # echo raw
            for ln in output.splitlines():
                self.log_line.emit(ln + "\n")

            # parse sections
            text_tsc, text_build = split_sections(output)
            self.log_line.emit("\n── TypeScript (tsc) ──\n")
            for ln in text_tsc.splitlines():
                self.log_line.emit(ln + "\n")
            self.log_line.emit("\n── Build (yarn build) ──\n")
            for ln in text_build.splitlines():
                self.log_line.emit(ln + "\n")

            combined = f"{text_tsc}\n{text_build}"

            # mine “Cannot find module …”
            self.module_list = self.find_missing_modules(text_build)
            if self.module_list:
                self.log_line.emit(f"\n🔧 Missing modules detected: {', '.join(self.module_list)}\n")
                if self.auto_install:
                    self.install_modules()

            # figure out file:line:col hits
            entries = get_error_entries(combined, self.project_path)
            src_prefix = os.path.normpath(os.path.join(self.project_path, 'src'))
            entries = [e for e in entries if e[0].startswith(src_prefix)]

            if not entries and 'use' in combined:
                entries = grep_use_imports(self.project_path)

            self.entries_found.emit(entries)

        except Exception:
            self.log_line.emit("\n❌ Exception in Worker:\n" + traceback.format_exc() + "\n")
            self.entries_found.emit([])

    def install_modules(self):
 
        
        for module in self.module_list:
            command = f"yarn add {module}"
            print(f"found it command =={command}")
            output = run_ssh_cmd(self.user, command, self.project_path)
            print(f"found it output =={output}")
            self.log_line.emit(output)

    def find_missing_modules(self, text_build: str):
        mods = []
        for line in text_build.splitlines():
            if 'Cannot find module' in line:
                # e.g. "Module not found: Error: Can't resolve 'xyz' in '/path'"
                # or TS2307
                parts = [s for s in line.split("'") if s and s != ' ']
                # usually parts[1] is the module name in CRA output; but keep it defensive
                cand = parts[1] if len(parts) > 1 else None
                if cand and not cand.startswith(('.', '/')) and cand not in mods:
                    mods.append(cand)
        return mods

    def install_modules(self):
        for module in self.module_list:
            cmd = f"yarn add {module}"
            self.log_line.emit(f"\n>>> {cmd}\n")
            output = run_ssh_cmd(self.user, cmd, self.project_path) if self.user else run_local_cmd(cmd, self.project_path)
            self.log_line.emit(output + "\n")
    def run_logs(self):
        self.module_list = []
        # Run remote build
        self.log_line.emit(f">>> SSH → {self.user}@…\n")
        output = run_ssh_cmd(self.user, COMMAND, self.project_path)
        # Emit raw output
        for line in output.splitlines():
            self.log_line.emit(line + "\n")

        # Wait for logs
        retries = 0
        while not (os.path.exists(self.tsc_log) and os.path.exists(self.build_log)):
            self.msleep(200)
            retries += 1
            if retries > 300:
                raise TimeoutError("Timed out waiting for log files.")

        # Read and clean logs
        self.text_tsc = strip_ansi(read_file(self.tsc_log))
        self.text_build = strip_ansi(read_file(self.build_log))
        self.combined = self.text_tsc + "\n" + self.text_build

        # Display build log
        self.log_line.emit("\n── Build Log ──\n")
        for line in self.text_build.splitlines():
            self.log_line.emit(line + "\n")
            #$logger.info(line)
            if 'Cannot find module' in line:
                print(f"found it {line}")
                modules = [string for string in line.split('Cannot find module')[-1].split("'") if string and string != ' ']
                if modules and isinstance(modules,list):
                    module = modules[0]
                    print(f"found it modules =={modules}")
                    logger.info(module)
                    if module not in self.module_list:
                        self.module_list.append(module)
                        print(f"found it module =={module}")
            print(f"found it module_list =={self.module_list}")
    def run(self):
        self.tsc_log = os.path.join(self.project_path, 'tsc.log')
        self.build_log = os.path.join(self.project_path, 'build.log')
        try:
            while True:
                self.run_logs()
                self.install_modules()
                input()
                if self.module_list == []:
                    break
                
            # Explicit error entries
            entries = get_error_entries(self.combined, self.project_path)
            # Filter to src folder
            src_prefix = os.path.normpath(os.path.join(self.project_path, 'src'))
            user_entries = [e for e in entries if e[0].startswith(src_prefix)]

            # If no explicit entries, try CRA bundler declarations
            if not user_entries:
                for ln in self.text_build.splitlines():
                    m = re.match(r"^\s*(?:\.?/)?(src/[^\s]+\.(?:ts|tsx|js|jsx))$", ln)
                    if m:
                        full = os.path.normpath(os.path.join(self.project_path, m.group(1)))
                        user_entries.append((full, 1, 1))
                if user_entries:
                    self.log_line.emit("\nℹ️ Bundler-declared file errors:\n")
                    for path,_,_ in user_entries:
                        self.log_line.emit(path + "\n")

            # Grep fallback for 'use' import errors
            if not user_entries and 'use' in self.combined:
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
            save_logs(self.tsc_log,self.build_log,self.project_path)
            for logf in (self.tsc_log, self.build_log):
                try:
                    if os.path.exists(logf): os.remove(logf)
                except Exception:
                    pass

# Main application window
class MainWindow(QWidget):
    def __init__(self,self_open=False):
        super().__init__()
        self.self_open= self_open
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
        auto = self.chk_auto.isChecked()
        self.worker = Worker(user, path, auto_install=auto)
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
                if self.self_open:
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
