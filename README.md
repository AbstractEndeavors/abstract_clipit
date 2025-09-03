# Abstract ClipIt

## Overview
Abstract ClipIt is a Python-based GUI application designed to simplify file management and analysis, particularly for developers. Built using PyQt6, it provides a drag-and-drop interface, a file system browser, and a logging console, enabling users to easily copy file contents to the clipboard, parse Python files for functions and imports, and manage file extensions and directories dynamically.

## Features
- **Drag and Drop Support**: Drag files or directories into the application to process their contents.
- **File System Browser**: Navigate and select files or folders via a tree view interface.
- **Clipboard Integration**: Copy file contents, function definitions, and import chains directly to the clipboard.
- **Extension Filtering**: Dynamically filter files by extension using checkboxes.
- **Directory Filtering**: Exclude or include specific directory patterns.
- **Function and Import Parsing**: Analyze Python files to extract function definitions and import dependencies.
- **Logging**: Toggleable log console for debugging and tracking actions.
- **View Toggle**: Switch between array and print views for text output.

## Installation
1. Ensure you have Python 3.6 or higher installed.
2. Install the required dependencies:
   ```bash
   pip install setuptools wheel abstract_utilities clipboard flask abstract_gui PyQt6
   ```
3. Clone the repository or download the source code.
4. Navigate to the project directory and install the package:
   ```bash
   python setup.py install
   ```

## Usage
### Running the Application
Run the application from the command line:
```bash
python -m abstract_clipit
```
This will launch the GUI with a file browser on the left, a drop area on the right, and a toggleable log console.

### Interface
- **Toolbar**: Contains buttons to toggle the log console and switch between view modes.
- **File System Tree**: Left pane for browsing and selecting files or folders. Double-click to process a file, or use the "Copy Selected" button.
- **File Drop Area**: Right pane where you can drag and drop files. Includes extension and directory filters, and displays function and file lists.
- **Log Console**: Bottom section (toggleable) for viewing application logs.

### Key Actions
- **Drag and Drop**: Drop files to read and copy their contents. Python files are parsed for functions and imports.
- **Browse Files**: Use the "Browse Files…" button to select multiple files via a dialog.
- **Copy Selected**: Copy selected items from the tree view to the drop area for processing.
- **Toggle Logs**: Show or hide the log console.
- **Toggle View**: Switch between array and print views for text output in the drop area.

## Directory Structure
```
abstract_clipit/
├── src/
│   ├── abstract_clipit/
│   │   ├── __init__.py
│   │   ├── imports.py
│   │   ├── main.py
│   │   ├── initFuncs.py
│   │   ├── FileDropArea/
│   │   │   ├── __init__.py
│   │   │   ├── imports.py
│   │   │   ├── main.py
│   │   │   ├── initFuncs.py
│   │   │   ├── functions/
│   │   │   │   ├── view_utils.py
│   │   │   │   ├── python_utils.py
│   │   │   │   ├── directory_utils.py
│   │   │   │   ├── rebuild_utils.py
│   │   ├── FileSystemTree/
│   │   │   ├── __init__.py
│   │   │   ├── imports.py
│   │   │   ├── main.py
│   │   │   ├── initFuncs.py
│   │   │   ├── functions/
│   │   │   │   ├── text_utils.py
│   │   ├── JSBridge/
│   │   │   ├── JSBridge.py
│   │   ├── clipitTab/
│   │   │   ├── __init__.py
│   │   │   ├── imports.py
│   │   │   ├── main.py
│   │   │   ├── initFuncs.py
│   │   │   ├── getFnames.py
│   │   │   ├── functions/
│   │   │   │   ├── drop_utils.py
│   │   ├── utils/
│   │   │   ├── read_utils.py
│   ├── imports/
│   │   ├── qt_funcs.py
│   │   ├── utils.py
├── setup.py
├── README.md
```

## Dependencies
- `abstract_utilities`
- `clipboard`
- `flask`
- `abstract_gui`
- `PyQt6`

## Development
### Contributing
Contributions are welcome! Please fork the repository, make your changes, and submit a pull request.

### Building
To build the package, run:
```bash
python setup.py sdist bdist_wheel
```

### Testing
Test the application by running it with sample files and verifying the clipboard output, log messages, and UI behavior.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.

## Contact
For support or inquiries, contact `partners@abstractendeavors.com`.
