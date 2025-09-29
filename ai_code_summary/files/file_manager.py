import os
import shutil
from pathlib import Path
from typing import List, Tuple

import pathspec
from loguru import logger

# Set of recognized code file extensions
_CODE_EXTENSIONS = {
    ".c",
    ".cpp",
    ".cs",
    ".css",
    ".default",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".md",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".yml",
    "Dockerfile",
}


def read_file(file_path: Path , tree: str ,append_tree :bool=True) -> Tuple[Path, str]:
    """
    Reads the content of a file.

    Args:
        file_path (Path): The path to the file to be read.

    Returns:
        Tuple[Path, str]: A tuple containing the file path and its content as a string.
    """
    try:
        with file_path.open("rb") as f:
            content = f.read().decode("utf-8", errors="ignore")
        if append_tree:
            content = str(file_path) + "\n"+ tree +"\n"+content
        logger.info(f"Read file {file_path}")
    except (OSError, UnicodeDecodeError) as e:
        logger.error(f"Error reading {file_path}: {e}")
        content = ""
    return file_path, content


def clear_tmp_folder(tmp_dir: Path) -> None:
    """
    Clears the contents of a temporary directory and recreates it.

    Args:
        tmp_dir (Path): The path to the temporary directory.
    """
    if tmp_dir.exists() and tmp_dir.is_dir():
        shutil.rmtree(tmp_dir)
        logger.info(f"Cleared contents of {tmp_dir}")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created directory {tmp_dir}")


def get_code_files(directory: str, spec: pathspec.PathSpec) -> List[Path]:
    """
    Retrieves a list of code files in a directory, excluding those that match the given pathspec.

    Args:
        directory (str): The directory to search for code files.
        spec (pathspec.PathSpec): The pathspec to filter out files.

    Returns:
        List[Path]: A list of paths to the code files.
    """
    base_dir = Path(directory)

    # Recursively collect all files in the directory
    all_files = [Path(root) / file for root, _, files in os.walk(base_dir) for file in files]

    # Filter files to include only code files
    code_files = [file for file in all_files if _is_code_file(file)]
    # Further filter files based on the pathspec
    filtered_files = [file for file in code_files if not spec.match_file(file.relative_to(base_dir))]

    logger.info(f"Found {len(filtered_files)} code files in {directory}")
    return filtered_files


def _is_code_file(file: Path) -> bool:
    """
    Checks if a file is a code file based on its extension or name.

    Args:
        file (Path): The file to check.

    Returns:
        bool: True if the file is a code file, False otherwise.
    """
    return file.suffix in _CODE_EXTENSIONS or file.name == "Dockerfile"


def write_files_to_tmp_directory(directory: str, spec: List[str], base_dir: Path, output_temp_code_dir: Path , tree: str) -> None:
    """
    Writes code files from a directory to a temporary directory, maintaining the directory structure.

    Args:
        directory (str): The directory to search for code files.
        spec (List[str]): The pathspec to filter out files.
        base_dir (Path): The base directory to calculate relative paths.
        output_temp_code_dir (Path): The directory where the files will be written.
    """
    code_files = get_code_files(directory, spec)
    file_contents = [read_file(file_path,tree) for file_path in code_files]
    [_write_file(file_info, base_dir, output_temp_code_dir) for file_info in file_contents]


def _write_file(file_info: Tuple[Path, str], base_dir: Path, output_dir: Path) -> None:
    """
    Writes content to a file in the specified output directory.

    Args:
        file_info (Tuple[Path, str]): A tuple containing the file path and its content.
        base_dir (Path): The base directory to calculate relative paths.
        output_dir (Path): The directory where the file will be written.
    """
    file_path, content = file_info

    # Calculate the relative path to maintain directory structure
    relative_path = file_path.relative_to(base_dir)
    output_file = output_dir / relative_path.name

    with output_file.open("w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"Wrote file {output_file}")


def get_tree(folder_path: str, show_hidden: bool = False, max_depth: int = None) -> str:
    """
    Create a professional tree structure for a local folder and return it as a formatted string.
    
    Args:
        folder_path (str): Path to the local folder
        show_hidden (bool): Whether to show hidden files/folders (default: False)
        max_depth (int): Maximum depth to traverse (None for unlimited)
    
    Returns:
        str: Formatted tree structure as a string
    
    Example:
        tree_output = create_folder_tree("/path/to/your/folder")
        print(tree_output)
    """
    import os
    from pathlib import Path
    
    def _should_include(name: str) -> bool:
        return show_hidden or not name.startswith('.')
    
    def _format_size(size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        if i == 0:
            return f"{int(size)} {size_names[i]}"
        else:
            return f"{size:.1f} {size_names[i]}"
    
    def _scan_directory(path: Path, current_depth: int = 0) -> dict:
        """Recursively scan directory structure."""
        if max_depth is not None and current_depth >= max_depth:
            return {}
        
        structure = {}
        try:
            items = [item for item in path.iterdir() if _should_include(item.name)]
            items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
            
            for item in items:
                try:
                    if item.is_dir():
                        structure[item.name] = {
                            'type': 'directory',
                            'size': 0,
                            'children': _scan_directory(item, current_depth + 1)
                        }
                    else:
                        structure[item.name] = {
                            'type': 'file',
                            'size': item.stat().st_size,
                            'children': {}
                        }
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            pass
        
        return structure
    
    def _format_tree(structure: dict, prefix: str = "", is_last_list: list = None) -> list:
        """Format the tree structure with proper indentation."""
        if is_last_list is None:
            is_last_list = []
        
        lines = []
        items = list(structure.items())
        
        for i, (name, data) in enumerate(items):
            is_last = i == len(items) - 1
            
            # Create the prefix for this line
            line_prefix = ""
            for is_ancestor_last in is_last_list:
                line_prefix += "    " if is_ancestor_last else "│   "
            
            line_prefix += "└── " if is_last else "├── "
            
            if data['type'] == 'directory':
                lines.append(f"{line_prefix}{name}/")
                # Recursively add children
                child_lines = _format_tree(
                    data['children'], 
                    prefix + ("    " if is_last else "│   "),
                    is_last_list + [is_last]
                )
                lines.extend(child_lines)
            else:
                size_info = f" [{_format_size(data['size'])}]" if data['size'] > 0 else ""
                lines.append(f"{line_prefix}{name}{size_info}")
        
        return lines
    
    # Main execution
    try:
        path = Path(folder_path).resolve()
        
        if not path.exists():
            return f"Error: Path '{folder_path}' does not exist."
        
        if not path.is_dir():
            return f"Error: Path '{folder_path}' is not a directory."
        
        structure = _scan_directory(path)
        
        if not structure:
            return f"{path.name}/\n└── (empty directory)"
        
        # Count total items
        def count_items(struct):
            count = len(struct)
            for item_data in struct.values():
                if item_data['type'] == 'directory':
                    count += count_items(item_data['children'])
            return count
        
        total_items = count_items(structure)
        
        # Count directories and files separately
        def count_types(struct):
            dirs, files = 0, 0
            for item_data in struct.values():
                if item_data['type'] == 'directory':
                    dirs += 1
                    sub_dirs, sub_files = count_types(item_data['children'])
                    dirs += sub_dirs
                    files += sub_files
                else:
                    files += 1
            return dirs, files
        
        dir_count, file_count = count_types(structure)
        
        result = []
        result.append(f"{path.name}/")
        result.append(f"├── Total items: {total_items}")
        result.append(f"├── Directories: {dir_count}")
        result.append(f"└── Files: {file_count}")
        result.append("")
        
        tree_lines = _format_tree(structure)
        result.extend(tree_lines)
        
        return "\n".join(result)
        
    except Exception as e:
        return f"Error: {str(e)}"


