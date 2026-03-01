import os
import subprocess
import requests
import re
def enforce_psycopg3_dependency():
    """
    Ensure psycopg2 / psycopg2-binary are NOT present in setup.py.
    Force psycopg[binary] instead.
    """
    with open("setup.py", "r") as f:
        content = f.read()

    original = content

    # Replace any psycopg2 variants
    content = re.sub(
        r"(psycopg2-binary|psycopg2)(\s*[<>=!~].*?)?(['\"])",
        r"psycopg[binary]\3",
        content,
    )

    # Also catch plain strings
    content = content.replace("'psycopg2'", "'psycopg[binary]'")
    content = content.replace('"psycopg2"', '"psycopg[binary]"')
    content = content.replace("'psycopg2-binary'", "'psycopg[binary]'")
    content = content.replace('"psycopg2-binary"', '"psycopg[binary]"')

    if content != original:
        with open("setup.py", "w") as f:
            f.write(content)
        print("🔧 Enforced psycopg[binary] dependency in setup.py")
    else:
        print("ℹ️ No psycopg2 dependency found in setup.py")
def ensure_pyproject_toml():
    """Ensure pyproject.toml exists in the current directory."""
    if not os.path.exists("pyproject.toml"):
        print("pyproject.toml not found. Creating pyproject.toml...")
        with open("pyproject.toml", "w") as f:
            f.write(
                "[build-system]\n"
                "requires = [\"setuptools>=42\", \"wheel\"]\n"
                "build-backend = \"setuptools.build_meta\"\n"
            )
        print("pyproject.toml created.")

def get_package_name():
    """Retrieve the package name from setup.py."""
    try:
        output = subprocess.check_output(
            ["python3", "setup.py", "--name"], universal_newlines=True
        )
        return output.strip()
    except subprocess.CalledProcessError:
        print("Error: Unable to determine package name from setup.py")
        exit(1)

def get_current_version(package_name):
    """Retrieve the current version of the package from PyPI."""
    try:
        response = requests.get(f"https://pypi.org/pypi/{package_name}/json")
        if response.status_code == 200:
            return response.json()["info"]["version"]
        else:
            print(f"Package {package_name} not found on PyPI. Using version 0.0.0.")
            return "0.0.0"
    except requests.RequestException as e:
        print(f"Error fetching current version from PyPI: {e}")
        exit(1)

def increment_version(version):
    """Increment the last numeric segment of the version."""
    parts = version.split(".")
    if not all(part.isdigit() for part in parts):
        print(f"Invalid version format: {version}")
        exit(1)

    # Increment the last segment
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)

def update_version_in_setup(current_version, new_version):
    """Update the version in setup.py."""
    with open("setup.py", "r") as f:
        setup_content = f.read()

    updated_content = re.sub(
        f"version=['\"]{current_version}['\"]",
        f"version='{new_version}'",
        setup_content,
    )

    with open("setup.py", "w") as f:
        f.write(updated_content)

    print(f"Updated setup.py with new version: {new_version}")

def build_package():
    """Build the package."""
    try:
        subprocess.run(["python3", "-m", "build", "--sdist", "--wheel"], check=True)
        print("Package built successfully.")
    except subprocess.CalledProcessError:
        print("Error during building the package.")
        exit(1)

def upload_package():
    """Upload the package to PyPI."""
    try:
        subprocess.run(["python3", "-m", "twine", "upload", "dist/*", "--skip-existing"], check=True)
        print("Package uploaded successfully.")
    except subprocess.CalledProcessError:
        print("Error during upload to PyPI.")
        exit(1)
        
def get_local_version(package_name):
    """Retrieve the installed version of the package in the local environment."""
    try:
        output = subprocess.check_output(
            ["pip", "show", package_name], universal_newlines=True
        )
        for line in output.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
        print(f"Package {package_name} is not installed locally.")
        return None
    except subprocess.CalledProcessError:
        print(f"Error checking local version for {package_name}")
        return None
    
def update_package(package_name):
    try:
        # Use bash interactive mode to ensure aliases are available
        subprocess.run(
            ["bash", "-i", "-c", f"pipit {package_name} --upgrade"],
            check=True
        )
        print("Package uploaded successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error during upload to PyPI: {e}")
        exit(1)
def update_to_specific(package_name,new_version):
    try:
        # Use bash interactive mode to ensure aliases are available
        subprocess.run(
            ["bash", "-i", "-c", f"pipit {package_name}=={new_version}"],
            check=True
        )
        print("Package uploaded successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error during upload to PyPI: {e}")
        exit(1)

def update_package_until_synced(package_name,new_version=None):
    """Update the local package until its version matches the PyPI version."""
    pypi_version = new_version or get_current_version(package_name)
    while True:
        update_to_specific(package_name,pypi_version)
        local_version = get_local_version(package_name)
        print(f"Local version: {local_version}, PyPI version: {pypi_version}")

        if local_version == pypi_version:
            print(f"{package_name} is up-to-date with PyPI.")
            break

        print(f"Updating {package_name} to match PyPI version...")
#        if new_version:
#            update_to_specific(package_name,new_version)
#        else:
        update_package(package_name)
import time
from typing import Optional

def wait_for_pypi_propagation(
    package_name: str,
    expected_version: str,
    max_wait_seconds: int = 180,
    check_interval: int = 10,
) -> bool:
    """
    Explicit wait for PyPI CDN propagation.
    
    Returns:
        True if version is available, False if timeout
    """
    print(f"Waiting for {package_name}=={expected_version} on PyPI CDN...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait_seconds:
        try:
            response = requests.get(
                f"https://pypi.org/pypi/{package_name}/json",
                timeout=5
            )
            if response.status_code == 200:
                available_version = response.json()["info"]["version"]
                if available_version == expected_version:
                    print(f"✓ Version {expected_version} available on PyPI")
                    return True
                print(f"PyPI shows {available_version}, waiting for {expected_version}...")
        except requests.RequestException as e:
            print(f"Check failed: {e}")
        
        time.sleep(check_interval)
    
    print(f"Timeout waiting for {expected_version}")
    return False


def install_package_explicit(package_name: str, version: str) -> bool:
    """
    Explicit pip install - no bash aliases.
    
    Returns:
        True if successful
    """
    try:
        subprocess.run(
            [
                "pip", "install", 
                f"{package_name}=={version}",
                "--upgrade",
                "--no-cache-dir",  # Force fresh download
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Install failed: {e.stderr}")
        return False


def verify_local_version(package_name: str, expected_version: str) -> bool:
    """Explicit version verification."""
    actual = get_local_version(package_name)
    if actual == expected_version:
        print(f"✓ Local install verified: {package_name}=={expected_version}")
        return True
    print(f"✗ Version mismatch: expected {expected_version}, got {actual}")
    return False


def main():
    ensure_pyproject_toml()
    
    package_name = get_package_name()
    enforce_psycopg3_dependency()
    update_package_until_synced(package_name)
    
    print(f"Package: {package_name}")
    
    current_version = get_current_version(package_name)
    new_version = increment_version(current_version)
    print(f"Version: {current_version} → {new_version}")
    
    # Update and build
    update_version_in_setup(current_version, new_version)
    
    if os.path.exists("dist"):
        print("Cleaning dist/...")
        for file in os.listdir("dist"):
            os.remove(os.path.join("dist", file))
    
    build_package()
    upload_package()
    
    # Explicit wait for propagation
    if not wait_for_pypi_propagation(package_name, new_version):
        print("WARNING: Timeout waiting for PyPI - proceeding anyway")
    
    # Explicit install with retry
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        print(f"Install attempt {attempt}/{max_retries}...")
        
        if install_package_explicit(package_name, new_version):
            if verify_local_version(package_name, new_version):
                print(f"✓ SUCCESS: {package_name}=={new_version} deployed and installed")
                return
        
        if attempt < max_retries:
            print(f"Retrying in 10s...")
            time.sleep(10)
    
    print(f"✗ FAILED: Could not verify local installation of {new_version}")
    exit(1)

if __name__ == "__main__":
    main()
