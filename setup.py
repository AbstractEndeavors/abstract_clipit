from time import time
import setuptools
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
setuptools.setup(
    name='abstract_clipit',
    version='0.0.1.54',
    author='putkoff',
    author_email='partners@abstractendeavors.com',
    description="Built using PyQt6, it provides a drag-and-drop interface, a file system browser, and a logging console, enabling users to easily copy file contents to the clipboard, parse Python files for functions and imports, and manage file extensions and directories dynamically.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/AbstractEndeavors/abstract_clipit',
    classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.11',
      ],
    install_requires=['PyQt6', 'abstract_gui', 'abstract_pandas', 'abstract_paths', 'abstract_utilities', 'pathlib', 'pdf2image', 'pytesseract'],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    # Add this line to include wheel format in your distribution
    setup_requires=['wheel'],
)
