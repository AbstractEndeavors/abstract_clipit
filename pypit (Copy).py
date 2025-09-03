import os
import subprocess
import requests
import re

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
def main():
    # Ensure pyproject.toml exists
    ensure_pyproject_toml()

    # Retrieve package name
    package_name = get_package_name()
    print(f"Package name: {package_name}")

    # Get current version from PyPI
    current_version = get_current_version(package_name)
    print(f"Current version on PyPI: {current_version}")

    # Increment version
    new_version = increment_version(current_version)

    # Update setup.py with new version
    update_version_in_setup(current_version, new_version)

    # Clean previous builds
    if os.path.exists("dist"):
        print("Cleaning up previous builds...")
        for file in os.listdir("dist"):
            os.remove(os.path.join("dist", file))

    # Build the package
    build_package()

    # Upload the package to PyPI
    upload_package()
    
    update_package_until_synced(package_name,new_version)


if __name__ == "__main__":
    main()
