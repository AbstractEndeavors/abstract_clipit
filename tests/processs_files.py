from abstract_utilities import *
from PyQt5 import QtCore, QtGui
logger =get_logFile(__name__)
logger.info('hoihohoho')
def make_drop_event(paths, pos=QtCore.QPointF(0, 0)):
    try:
        mime = QtCore.QMimeData()
        logger.info(mime)
        urls = [QtCore.QUrl.fromLocalFile(p) for p in paths]
        logger.info(urls)
        mime.setUrls(urls)
        paths = [url.toLocalFile() for url in make_list(mime.urls())]
        return paths
    except Exception as e:
        logger.info(e)
##path = "/run/user/1000/gvfs/sftp:host=192.168.0.100,user=root/var/www/modules/build-all.sh"
##content = read_from_file(path)
##dirname = os.path.dirname(path)
##dirlist = os.listdir(dirname)
##for content in dirlist:
##    path = os.path.join(dirname,content)
##    isfile = os.path.isfile(path)
##    print(f"isfile == {isfile}")
##    input(path)
paths = make_drop_event(["sftp://root@192.168.0.100/var/www/modules"])
for path in paths:
    isfile = os.path.isfile(path)
    if isfile:
        content = read_from_file(path)
        input(content)
    else:
        dirlist = os.listdir(path)
        input(dirlist)
def get_contents_text(self, file_path: str, idx: int = 0, filtered_paths: list[str] = []):
    basename = os.path.basename(file_path)
    filename, ext = os.path.splitext(basename)
    if ext not in self.exclude_exts:
        header = f"=== {file_path} ===\n"
        footer = "\n\n――――――――――――――――――\n\n"
        info = {
            'path': file_path,
            'basename': basename,
            'filename': filename,
            'ext': ext,
            'text': "",
            'error': False,
            'visible': True
        }
        try:
            body = read_file_as_text(file_path) or ""
            if isinstance(body, list):
                body = "\n".join(body)
            info["text"] = [header, body, footer]
            if ext == '.py':
                self._parse_functions(file_path, str(body))
        except Exception as exc:
            info["error"] = True
            info["text"] = f"[Error reading {basename}: {exc}]\n"
            self._log(f"Error reading {file_path} → {exc}")
        return info

def process_files(self, paths: list[str] = None) -> None:
    paths = make_list(paths or [])
    filtered = paths
    self._rebuild_ext_row(filtered)
    self._rebuild_dir_row(filtered)
    filtered_paths=[]
    if self.ext_checks or self.dir_checks:
        visible_exts = {ext for ext, cb in self.ext_checks.items() if cb.isChecked()}
        visible_dirs = {di for di, cb in self.dir_checks.items() if cb.isChecked()}
        
        self._log(f"Visible extensions: {visible_exts}")
        filtered_paths = [
            p for p in filtered
            if (os.path.isdir(p) or os.path.splitext(p)[1].lower() in visible_exts) and not is_string_in_dir(p,list(visible_dirs))
        ]
    else:
        filtered_paths  = filtered
    if not filtered_paths:
        self.text_view.clear()
        self.status.setText("⚠️ No files match current extension filter.")
        return
    self.status.setText(f"Reading {len(filtered_paths)} file(s)…")
    QtWidgets.QApplication.processEvents()
    self.combined_text_lines = {}
    self.functions = []
    self.python_files = []
    for idx, p in enumerate(filtered_paths, 1):
        info = self.get_contents_text(p, idx, filtered_paths)
        if info:
            self.combined_text_lines[p] = info
            if info['ext'] == '.py':
                self.python_files.append(info)
    self._populate_list_view()
    self._populate_text_view()
    self.status.setText("Files processed. Switch tabs to view.")
