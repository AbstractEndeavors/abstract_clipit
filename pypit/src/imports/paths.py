import os
def get_abs_path():
    return os.path.abspath(__file__)
def get_abs_dir():
    return os.path.dirname(get_abs_path())
def get_src_dir():
    return os.path.dirname(get_abs_dir())
def get_env_dir():
    return os.path.dirname(get_src_dir(),'envs')
def get_local_env():
    return os.path.join(get_env_dir(), '.env')
def get_pre_path():
    return get_env_value(path=get_local_env(), key='ENV_PATH')
def get_pre_key():
    return get_env_value(path=get_local_env(), key='ENV_KEY')
def get_init_env_path():
    return get_env_value(path=get_pre_path(), key=get_pre_key())
def get_init_owner_env_value(key):
    return get_env_value(path=get_pre_path(), key=key)
def get_owner_name_key(i):
    return get_init_owner_env_value(f"GITHUB_OWNER_{i}")
def get_owner_tok_key(i):
    return get_init_owner_env_value(f"GITPASS_{i}")
def get_owner_env_value(key):
    return get_env_value(path=get_init_env_path(), key=key)
def get_owner_name_value(i):
    return get_owner_env_value(get_owner_name_key(i))
def get_owner_tok_value(i):
    return get_owner_env_value(get_owner_tok_key(i))
def get_git_key_path():
    return "~/.ssh/github/githubssh_nopass"
def get_ssh_config_path():
    return "~/.ssh/config"
def get_owner_name(i):
    return get_owner_name_value(i)
def get_owner_tok(i):
    return get_owner_tok_value(i)
