import os
from abstract_utilities import *
from abstract_utilities.import_utils import get_file_parts

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = os.getcwd()   # The directory you're calling from
TARGET_PARTS = get_file_parts(TARGET_DIR)
TARGET_PARTS["imports"] = []
files = collect_globs(TARGET_DIR, allowed_exts=['.py'], add=True, file_type='f')

all_dirs = {TARGET_DIR:TARGET_PARTS}

for file in files:
    file_parts = get_file_parts(file)
    dirname = file_parts.get("dirname")

    # Don't ever modify this tool's own folder
    if dirname.startswith(SCRIPT_DIR):
        continue

    if dirname not in all_dirs:
        all_dirs[dirname] = {
            "imports": [],
            "dirbase": file_parts.get("dirbase"),
            "parent_dirname": file_parts.get("parent_dirname")
        }

    filename = file_parts.get("filename")

    if filename != "__init__":
        all_dirs[dirname]["imports"].append(f"from .{filename} import *")

# handle subfolder imports
for dirname, values in all_dirs.items():
    for comp_dir, comp_values in all_dirs.items():
        comp_parent_dirname = comp_values.get("parent_dirname")
        if comp_parent_dirname == dirname:
            values["imports"].append(f"from .{comp_values['dirbase']} import *")
    # write __init__.py
    init_path = os.path.join(dirname, "__init__.py")
    contents = "\n".join(values["imports"]) + "\n"
    
    write_to_file(file_path=init_path, contents=contents)
##
print("Done.")
