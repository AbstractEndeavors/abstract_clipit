import os
import ast
import subprocess
import shutil
from abstract_utilities import *
from abstract_utilities.cmd_utils import *
logger = get_logFile('npmIt')
def cmd_run(cmd: str, output_text: str = None, print_output: bool = False) -> None:
    if output_text is None:
        output_text = get_output_text()

    # Clear output file
    with open(output_text, 'w') as f:
        pass

    # Append output redirection
    full_cmd = f'{cmd} >> {output_text}; echo END_OF_CMD >> {output_text}'

    if print_output:
        print(full_cmd)

    subprocess.call(full_cmd, shell=True)

    # Wait until END_OF_CMD appears
    while True:
        get_sleep(sleep_timer=0.5)
        with open(output_text, 'r') as f:
            lines = f.readlines()
            
            if lines and lines[-1].strip() == 'END_OF_CMD':
                os.remove(output_text)
                return lines

    if print_output:
        with open(output_text, 'r') as f:
            print_cmd(full_cmd, f.read().strip())

    os.remove(output_text)
def get_current_dir():
    current_path_manager = get_current_path_manager()
    return current_path_manager.curr_dir

def get_abs_path():
    return os.path.abspath(__file__)

def get_abs_dir():
    abs_path = get_abs_path()
    return os.path.dirname(abs_path)

def get_local_dir():
    local_dir = os.getcwd()
    if local_dir != get_current_dir():
        change_dir(local_dir)
    return local_dir

class currentPathManager(metaclass=SingletonMeta):
    def __init__(self):
        if not hasattr(self, 'initialized') or self.initialized == False:
            self.initialized = True
            self.curr_dir = os.getcwd()
    def change_dir(self, directory):
        if directory and os.path.isdir(directory) and self.curr_dir != directory:
            self.curr_dir = directory

def get_current_path_manager():
    return currentPathManager()

def change_dir(directory=None):
    directory = directory or os.getcwd()
    current_path_manager = get_current_path_manager()
    if directory != current_path_manager.curr_dir:
        current_path_manager.change_dir(directory=directory)

def get_local_file(file):
    abs_dir = get_current_dir()
    local_file_path = os.path.join(abs_dir, file)
    return local_file_path

def get_package_path():
    return get_local_file('package.json')

def get_package_data():
    package_path = get_package_path()
    data = safe_read_from_json(package_path)
    return data

def get_package_values(key):
    data = get_package_data() or {}
    return data.get(key)

def get_module_version(module, key=None):
    if key:
        package_values = get_package_values(key)
        return package_values.get(module)
    else:
        dependencies = [get_package_dependencies(), get_package_dev_dependencies()]
        for dependency in dependencies:
            for key, value in dependency.items():
                if key in module:
                    return value

def get_all_module_versions(module):
    execute = ['npm', 'view', module, 'versions']
    result = get_cmd_out(' '.join(execute))
    text = result[0].decode('utf-8')
    try:
        versions = ast.literal_eval(str(text))
    except (SyntaxError, ValueError):
        logger.error(f"Failed to parse versions for {module}: {text}")
        versions = []
    return versions

def get_latest_module_release(module):
    all_module_versions = get_all_module_versions(module)
    version = '0.0.0'
    if all_module_versions:
        version = all_module_versions[-1]
    return str(version)

def get_section(section):
    return int(section) if section.isdigit() else 0

def output_zeroes(obj, comp_obj):
    obj = list(obj)
    comp_obj = list(comp_obj)
    len_obj = len(obj)
    len_comp = len(comp_obj)
    if len_obj >= len_comp:
        largest = obj
        smallest = comp_obj
        zeroes = len_obj - len_comp
    else:
        largest = comp_obj
        smallest = obj
        zeroes = len_comp - len_obj
    for _ in range(zeroes):
        smallest.append("0")
    for i in range(len(largest)):
        len_largest = len(largest[i])
        len_smallest = len(smallest[i])
        max_section_len = max(len_largest, len_smallest)
        largest[i] = largest[i].zfill(max_section_len)
        smallest[i] = smallest[i].zfill(max_section_len)
    return obj, comp_obj

def check_npm_login():
    status,result = run_all_cmd(['npm', 'whoami'], check=False)
    if status ==False:
        logger.error("Not logged into npm. Run 'npm login' or set NPM_TOKEN.")
        return False
    logger.info(f"Logged in as: {result.stdout.strip()}")
    return True

def is_old_version(module, key=None):
    module_version = eatAll(get_module_version(module=module, key=key), '^')
    latest_module_release = eatAll(get_latest_module_release(module), '^')
    logger.info(f'module_version = {module_version}')
    logger.info(f'latest_module_release = {latest_module_release}')
    if not module_version or not latest_module_release:
        logger.info(f'No version found for {module}, assuming outdated')
        return True
    current_version_spl = module_version.split('.')
    latest_module_version_spl = latest_module_release.split('.')
    current_version_spl, latest_module_version_spl = output_zeroes(current_version_spl, latest_module_version_spl)
    for i, latest_section in enumerate(latest_module_version_spl):
        latest_num = get_section(latest_section)
        current_num = get_section(current_version_spl[i]) if i < len(current_version_spl) else 0
        logger.info(f'Comparing section {i}: current={current_num}, latest={latest_num}')
        if latest_num > current_num:
            logger.info(f'{module} is old: {module_version} < {latest_module_release}')
            return True
        elif latest_num < current_num:
            logger.info(f'{module} is newer: {module_version} > {latest_module_release}')
            return False
    logger.info(f'{module} is up-to-date: {module_version} == {latest_module_release}')
    return False

def get_package_version():
    return get_package_values('version')

def get_package_dependencies():
    return get_package_values("dependencies") or {}

def get_package_dev_dependencies():
    return get_package_values("devDependencies") or {}

def get_putkoff_packages():
    found_putkoffs = []
    dependencies = [get_package_dependencies(), get_package_dev_dependencies()]
    for dependency in dependencies:
        for key, value in dependency.items():
            if key.startswith('@putkoff'):
                found_putkoffs.append(key)
    return found_putkoffs

def get_executors(isYarn=False):
    executor = 'npm'
    exec_remove = 'uninstall'
    exec_add = 'install'
    build = ['run', 'build']
    if isYarn:
        executor = 'yarn'
        exec_remove = 'remove'
        exec_add = 'add'
        build = ['build']
    return executor, exec_remove, exec_add, build

def make_putkoff_package(name):
    return f"@putkoff/{name}"

def get_current_package_last_release():
    name = get_abstract_name()
    putkoff_package = make_putkoff_package(name)
    latest_module_release = get_latest_module_release(putkoff_package)
    return latest_module_release

def get_new_version_number_of_current_package():
    version = get_current_package_last_release()
    package_version = get_package_version()
    new_version = get_new_version(version)
    logger.info(f"Latest published: {version}, Current: {package_version}, New: {new_version}")
    return new_version

def get_update_packages(isYarn=False, abs_dir=None):
    abs_dir = abs_dir or get_current_dir()
    executor, exec_remove, exec_add, build = get_executors(isYarn=isYarn)
    putkoff_defaults = {
        "secure-files": ["abstract-utilities", "abstract-files", "abstract-logins", "abstract-apis"],
        "abstract-utilities": [],
        "abstract-files": ["abstract-utilities"],
        "abstract-logins": ["abstract-utilities", "abstract-files"],
        "abstract-apis": ["abstract-utilities"]
    }
    package_name = get_package_name()
    putkoff_defs = putkoff_defaults.get(package_name, [])
    putkoff_def_needs = [make_putkoff_package(pack) for pack in putkoff_defs]
    putkoff_packages = list(set(putkoff_def_needs + get_putkoff_packages()))
    #input(f"putkoff_packages: {putkoff_packages}")
    outdated_packages = [module for module in putkoff_packages if is_old_version(module)  or module in putkoff_def_needs]
    #input(f"Outdated packages: {outdated_packages}")
    for putkoff_package in outdated_packages:
        logger.info(f"Updating {putkoff_package}")
        status,result = run_all_cmd([executor, exec_remove, putkoff_package])
        if status == False:
            logger.error(f"Failed to uninstall {putkoff_package}")
        status,result = run_all_cmd([executor, exec_add, f"{putkoff_package}@latest"])
        if status == False:
            logger.error(f"Failed to install {putkoff_package}")
    return outdated_packages

def get_version_split(version):
    return str(version).split('.')

def replace_ver_part(version, ver_part, i):
    if isinstance(version, list):
        version_spl = version
    else:
        version_spl = get_version_split(version)
    version_spl[i] = ver_part
    return version_spl

def get_new_version(version):
    version_spl = get_version_split(version)  # Splits "0.1.195" → ["0", "1", "195"]
    version_spl_copy = version_spl.copy()
    for i, vers in enumerate(reversed(version_spl)):  # Iterates ["195", "1", "0"]
        ver_len = len(vers)  # Length of string, e.g., "195" → 3
        if ver_len < 3:
            vers = '000'[ver_len:]  # Pads to 3 digits, e.g., "1" → "001"
            
        ver_length = len(vers)  # Length after padding
        num = '1' + '0' * ver_length  # "1" + zeros, e.g., "1000" for 3 digits
        ver_zeros = '0' * ver_length  # Zeros, e.g., "000"
        max_ver_num = int(num)  # e.g., "1000" → 1000
        ver_new = str(int(vers) + 1)  # Increment, e.g., "195" → "196"
        ver_part = ver_zeros[:-len(ver_new)] + ver_new  # Pad, e.g., "196" → "196"
        c = len(version_spl) - 1 - i  # Index in original list, e.g., 2 for "195"
        if int(ver_new) != max_ver_num:  # If not max (e.g., 196 ≠ 1000)
            version_spl_copy = replace_ver_part(version_spl_copy, ver_new, c)  # Update, e.g., ["0", "1", "196"]
            break
        else:
            version_spl_copy = replace_ver_part(version_spl_copy, ver_zeros, c)  # Reset to "0", e.g., ["0", "1", "0"]
    return '.'.join(version_spl_copy)  # Join, e.g., "0.1.196"

def get_node_modules_dir():
    return get_local_file('node_modules')

def get_dist_dir():
    return get_local_file('dist')

def get_package_name():
    return get_package_values("name")

def get_abstract_name():
    package_name = get_package_name()
    if package_name.startswith('abstract'):
        return package_name

def get_lock_paths():
    dirname = get_current_dir()
    dirlist = os.listdir(dirname)
    locks = [os.path.join(dirname, item) for item in dirlist if item.endswith('.lock')]
    return locks

def get_package_lock(package=None):
    package = package or 'package'
    lock_paths = get_lock_paths()
    package_lock = [path for path in lock_paths if package in os.path.basename(path)]
    if package_lock:
        return package_lock[0]

def remove_lock(package=None):
    package_lock = get_package_lock(package=package)
    if package_lock:
        os.remove(package_lock)

def remove_package_lock():
    remove_lock(package='package')

def remove_yarn_lock():
    remove_lock(package='yarn')

def remove_locks():
    remove_package_lock()
    remove_yarn_lock()

def remove_dir(directory):
    if os.path.isdir(directory):
        shutil.rmtree(directory)

def remove_node_modules():
    node_modules_dir = get_node_modules_dir()
    remove_dir(node_modules_dir)

def remove_dist():
    dist_dir = get_dist_dir()
    remove_dir(dist_dir)
def get_onlu_nums(obj):
    nums=''
    for char in str(obj):
        if is_number(char):
            nums+=str(char)
    return nums
def make_zeroes(obj,num=3):
    obj = get_onlu_nums(obj)
    if len(obj) >num:
        num = len(obj)
    for i in range(num):
        if len(obj)<=i:
            obj+='0'
    return obj
def get_zeroes(vers='',comp_vers=''):
    vers = str(vers)
    len_vers= len(vers)
    comp_vers = str(comp_vers)
    len_comp_vers = len(comp_vers)
    if len_comp_vers > len_vers:
       zeroes = ''
       for j in range(len_comp_vers):
           zero='0'
           if i<len_vers:
               zero = vers[i]
           zeroes+=zero
       return zeroes,comp_vers
    if  len_vers > len_comp_vers :
       zeroes = ''
       for j in range(len_vers):
           zero='0'
           if j<len_comp_vers:
               zero = comp_vers[j]
           zeroes+=zero
       return vers,zeroes
    return vers,comp_vers
def output_zeros(v1: str, v2: str):
    # 1) Split into integer lists
    parts1 = [int(x) for x in v1.split('.')]
    parts2 = [int(x) for x in v2.split('.')]

    # 2) Pad both lists to the same length
    max_len = max(len(parts1), len(parts2))
    parts1 += [0] * (max_len - len(parts1))
    parts2 += [0] * (max_len - len(parts2))

    # 3) Decide how wide each component needs to be
    max_width = max(
        max(len(str(n)) for n in parts1),
        max(len(str(n)) for n in parts2)
    )

    # 4) Build a format string like "{:03d}" if max_width==3
    fmt = f"{{:0{max_width}d}}"

    # 5) Return the zero-padded dotted versions
    norm1 = '.'.join(fmt.format(n) for n in parts1)
    norm2 = '.'.join(fmt.format(n) for n in parts2)
    return norm1, norm2
def get_larger_version(v1,v2):
    v1,v2 = output_zeros(v1, v2)
    parts1 = [int(x) for x in v1.split('.')]
    parts2 = [int(x) for x in v2.split('.')]
    for i,part in enumerate(parts1):
        if int(parts2[i]) > int(part):
            return v2
        if int(parts2[i]) < int(part):
            return v1
    return v1
def ground_zeroes(obj):
    obj = [str(int(x)) for x in obj.split('.')]
    return '.'.join(obj)
def apply_package_version_update(new_version):
    package_path = get_package_path()
    package_data = get_package_data()
    package_name = get_abstract_name()
    putkoff_package = make_putkoff_package(package_name)
    version = get_all_module_versions(putkoff_package)
    new_version = version[-1]
    package_version =get_package_version()
    new_version,package_version  = output_zeros(new_version,package_version)
    larger_version = get_larger_version(new_version,package_version)

    package_data['version'] = output_zeroes(new_version, version[-1])
    if larger_version  <= package_version:
        larger_version = get_new_version(package_version)
    if larger_version <= new_version:
        larger_version = get_new_version(new_version)
    package_data['version'] = ground_zeroes(larger_version)

    safe_dump_to_json(data=package_data, file_path=package_path)

def update_package_version():
    version = get_package_version()
    name = get_abstract_name()
    putkoff_package = make_putkoff_package(name)
    new_version = get_latest_module_release(putkoff_package)
    new_version = get_new_version(new_version)
    logger.info(f"Updating version from {version} to {new_version}")
    apply_package_version_update(new_version)
    return new_version

def get_secure_files_dir():
    secure_files_dir = '/var/www/html/abstractendeavors/secure-files'
    change_dir(secure_files_dir)
    return secure_files_dir
def run_cmd(cmd, cwd=None, check=None, is_yarn=False):
    """
    Run `cmd` (a list of args, or a shell string with shell=True), capture its
    stdout/stderr as text, and return a subprocess.CompletedProcess.
    """
    if isinstance(cmd, (list, tuple)):
        # exec without shell, args are already split
        return subprocess.run(cmd,
                              cwd=cwd,
                              check=check,
                              capture_output=True,
                              text=True)
    else:
        # run as a shell line
        return subprocess.run(cmd,
                              shell=True,
                              cwd=cwd,
                              check=check,
                              capture_output=True,
                              text=True)

def try_run_all_cmd(cmd, cwd=None, check=None,  isYarn=False):
    """
    Runs `cmd` (a list) in cwd, auto-fixing two npm/rollup failures:
    1) “Cannot find module …” → npm uninstall/install that module
    2) “Run `yarn install` to generate one” → yarn install then retry
    Returns (ok: bool, cp: CompletedProcess).
    """
    npm, rm, add, _ = get_executors(isYarn=isYarn)
    cp = subprocess.run(cmd,
                        cwd=cwd,
                        check=False,
                        capture_output=True,
                        text=True)

    # Case A: missing module
    if cp.returncode != 0 and "Cannot find module " in cp.stderr:
        missing = cp.stderr.split("Cannot find module ")[1].split()[0].strip("'\"")
        # uninstall & reinstall the missing @putkoff package
        subprocess.run([npm, rm, missing], cwd=cwd, check=False)
        subprocess.run([npm, add, f"{missing}@latest"], cwd=cwd, check=True)
        # retry
        return run_with_fixes(cmd, cwd=cwd, is_yarn=is_yarn)

    # Case B: asking for yarn install
    if cp.returncode != 0 and "Run `yarn install` to generate one" in cp.stderr:
        subprocess.run("yarn install", cwd=cwd, shell=True, check=True)
        return run_with_fixes(cmd, cwd=cwd, is_yarn=is_yarn)

    # final result
    return (cp.returncode == 0), cp

    
def run_all_cmd(execute, directory=None, check=None, isYarn=False):
    check = True if check in [None, True, 1, 'true', 'True', 'TRUE'] else False
    directory = directory or get_current_dir()
    logger.info(f"Executing: {' '.join(execute)} in {directory}")
    return try_run_all_cmd(execute,directory,check=check, isYarn=isYarn)
def try_with_error(e):
    error_output = e.stdout + e.stderr
  
    if "Cannot find module '@putkoff/abstract-utilities'" in error_output:
        logger.info("Detected missing @putkoff/abstract-utilities, installing...")
        status,install_result = run_all_cmd(
            ['npm', 'install', '@putkoff/abstract-utilities@latest'],
            check=True
        )
        if status == False:
            logger.info("Olivejuice, installed @putkoff/abstract-utilities!")
            return False,'continue'
        else:
            logger.error(f"Failed to install @putkoff/abstract-utilities: Stdout: {install_result.stdout}, Stderr: {install_result.stderr}")
            return False,'break'
    logger.error(f"Build failed: Stdout: {e.stdout}, Stderr: {e.stderr}")
    if attempts == max_attempts:
        logger.error(f"Max build attempts ({max_attempts}) reached, giving up")
        return False,e
def run_build(isYarn=False, directory=None, check=None, max_attempts=3):
    abs_dir = directory or get_current_dir()
    executor, _, _, build = get_executors(isYarn=isYarn)
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        return_code=None
        logger.info(f"Build attempt {attempts}/{max_attempts} in {abs_dir}")
        try:
            status,result = run_all_cmd([executor] + build,  check=check)
            
            logger.info(f"Olivejuice, build succeeded on attempt {attempts}!")
            if status == False:
                status,return_code = try_with_error(result)
        except subprocess.CalledProcessError as e:
            status,return_code = try_with_error(result)
        if return_code:
            if return_code == 'break':
                break
        if status == True:
            return status,return_code 
    return status,return_code 
def run_publish(isYarn=False, directory=None, check=None):
    executor, _, _, _ = get_executors(isYarn=isYarn)
    abs_dir = directory or get_current_dir()

    # Only one attempt — if E403, treat as “already published” success
    logger.info(f"Publishing in {abs_dir}")
    try:
        status, result = run_all_cmd([executor, 'publish', '--access', 'public'], directory=abs_dir, check=True)
        return True, result
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").lower()
        if "you cannot publish over the previously published versions" in stderr:
            logger.warning("Version was already published. Skipping rollback.")
            return True, e
        logger.error(f"Publish failed: {e.stderr}")
        return False, e
def build_main(isYarn=False, directory=None, check=None):
    status,result = run_all_cmd(['yarn', 'build'], directory=directory, check=check)
    return status,result

def run_and_publish(isYarn=False):
    original_version = get_package_version()
    new_version = update_package_version()
    abs_dir = get_current_dir()
    remove_dist()
    remove_node_modules()
    remove_locks()
    if not check_npm_login():
        logger.error("Aborting publish due to login failure")
        apply_package_version_update(original_version)
        return False
    build_status = run_build(isYarn=isYarn)
    if build_status is False or (isinstance(build_status, subprocess.CalledProcessError) and build_status.returncode != 0):
        logger.error(f"Build failed: {getattr(build_status, 'stderr', 'No stderr')} {getattr(build_status, 'stdout', 'No stdout')}")
        apply_package_version_update(original_version)
        return False
    ok, pub_result = run_publish(isYarn)
    if not ok:
        # Only roll back on “real” publish failures
        apply_package_version_update(original_version)
        return False

    logger.info(f"Successfully published {new_version}")
    return True

if __name__ == "__main__":
    revert_dir = get_current_dir()
    
    change_dir()
    package_name = get_abstract_name()
    logger.info(f"package_name == {package_name}")
   
    isYarn = len(get_package_lock(package='yarn') or []) > 0
    version = get_package_version()

    remove_yarn_lock()
    logger.info('remove_yarn_lock')
    remove_package_lock()
    logger.info('remove_package_lock')
    remove_dist()
    logger.info('remove_dist')
    remove_node_modules()
    logger.info('remove_node_modules')
    get_update_packages(isYarn=isYarn)
    logger.info('get_update_packages')
    status = run_and_publish(isYarn=isYarn)
    logger.info(f"run_and_publish == {status}")
    if status is False:
        logger.info(f"Reverting to version {version}")
        apply_package_version_update(version)
    else:
        package_name = get_abstract_name()
        logger.info(f"package_name == {package_name}")
        if package_name:
            abs_dir = get_secure_files_dir()
            logger.info(f"get_secure_files_dir == {abs_dir}")
            logger.info(f"abs_dir == {abs_dir}")
            get_update_packages(isYarn=True, abs_dir=abs_dir)
            logger.info(f"get_update_packages")
            build_main(isYarn=True)
            logger.info(f"build_main")
    change_dir(revert_dir)
