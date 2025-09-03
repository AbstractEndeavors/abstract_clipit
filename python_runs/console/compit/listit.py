from abstract_utilities import *
from abstract_paths.content_utils.file_utils import *
import os
files = findGlobFiles('/var/www/TDD/my-app/src/pages')
input(files)
#write_to_file(file_path='page_list.txt',contents='\n'.join(files).replace('"','').replace("'",''))
#print(files)
dirs = [file for file in files if os.path.isdir(file) and 'variables.json' in  os.listdir(file) and 'content.md' in os.listdir(file)]
input(dirs)
for directory in dirs:
    dirlist = os.listdir(directory)
    print(dirlist)
    file_list = [os.remove(os.path.join(directory,basename)) for basename in dirlist if basename and basename not in ['content.md','variables.json']]
    for file in file_list:
        if file and os.path.exists(file):
            os.remove(file)
    
        
