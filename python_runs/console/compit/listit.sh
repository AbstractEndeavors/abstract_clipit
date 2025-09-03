from abstract_utilities import *
from abstract_paths.content_utils.file_utils import *
files = findGlobFiles(os.getcwd())
files = [file.replace('/run/user/1000/gvfs/sftp:host=192.168.0.100,user=solcatcher','') for file in files]
input(files)
dirs=[]
files= []
for file in files:
    if os.path.isdir(file):
        dirs.append(file)
    elif os.path.isfile(file):
        files.append(file)
