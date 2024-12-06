import os
import sys
import fnmatch
import re
from typing import List, Tuple, Set, Dict

# Constants
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UTILS_DIR = os.path.join(ROOT_DIR, 'utils')
OUTPUT_DIR = os.path.join(UTILS_DIR, 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

FILE_TYPES = ['.js', '.jsx', '.ts', '.tsx', '.prisma', '.md', '.scss', '.css', '.mdx']
EXCLUDE_FOLDERS = ['.next', 'node_modules', '.vscode', '.git', '.contentlayer', '.husky', 'utils']
EXCLUDE_FILES = ['package-lock.json', '*.log', '*.lock', '*.env', '*.test.js', '*.spec.js', '*.map', 'pnpm-lock.yaml', 'pnpm-workspace.yaml']
INCLUDE_SUBDIRS = ['app', 'src', 'pages', 'components', 'lib', 'models', 'api']
RELEVANT_FILES = ['trello', 'board', 'card', 'list', 'cloudinary', 'image', 'upload', 'prisma', 'schema', 'model']

DEPENDENCY_PATTERN = r"import\s+.*?from\s+['\"]([^'\"]+)['\"]"

def get_all_files(root_dir: str) -> Tuple[List[str], List[str], List[str]]:
    all_files, included_files, excluded_files = [], [], []

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_FOLDERS]

        if not any(subdir in root for subdir in INCLUDE_SUBDIRS):
            continue

        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, root_dir)

            if file.lower().endswith(tuple(FILE_TYPES)) and not any(fnmatch.fnmatch(file, pattern) for pattern in EXCLUDE_FILES):
                if any(keyword in relative_path.lower() for keyword in RELEVANT_FILES):
                    included_files.append(relative_path)
                else:
                    excluded_files.append(relative_path)
            else:
                excluded_files.append(relative_path)

            all_files.append(relative_path)

    return all_files, included_files, excluded_files

def extract_dependencies(file_path: str) -> Set[str]:
    dependencies = set()
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        matches = re.findall(DEPENDENCY_PATTERN, content)
        for match in matches:
            if not match.startswith('.'):
                dependencies.add(match.split('/')[0])
    return dependencies

def write_source_files(included_files: List[str], excluded_files: List[str], output_file: str, root_dir: str) -> Set[str]:
    all_dependencies = set()
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("// Included files:\n")
        for file in included_files:
            f.write(f"// {file}\n")
            try:
                file_path = os.path.join(root_dir, file)
                with open(file_path, 'r', encoding='utf-8') as source_file:
                    f.write(source_file.read())

                dependencies = extract_dependencies(file_path)
                all_dependencies.update(dependencies)
            except Exception as e:
                f.write(f"// Error reading file: {str(e)}\n")
            f.write('\n\n')

        f.write("\n// Excluded files:\n")
        for file in excluded_files:
            f.write(f"// {file}\n")

    return all_dependencies

def process_directory(dir_name: str, dir_path: str) -> Tuple[str, Tuple[List[str], List[str]], Set[str]]:
    all_files, included_files, excluded_files = get_all_files(dir_path)

    if all_files:
        output_file = os.path.join(OUTPUT_DIR, f'{dir_name}_source_files.txt')
        dependencies = write_source_files(included_files, excluded_files, output_file, dir_path)
        print(f"Files from {dir_name} have been processed and written to: {output_file}")
        print(f"  Included files: {len(included_files)}")
        print(f"  Excluded files: {len(excluded_files)}")
    else:
        print(f"No files found in {dir_name}")
        dependencies = set()

    return dir_path, (included_files, excluded_files), dependencies

def generate_summary(processed_dirs: Dict[str, Tuple[str, Tuple[List[str], List[str]], Set[str]]]):
    summary_file = os.path.join(OUTPUT_DIR, 'summary.txt')
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("Application Structure Summary:\n\n")
        all_dependencies = set()
        for dir_name, (dir_path, (included_files, excluded_files), dependencies) in processed_dirs.items():
            all_files = included_files + excluded_files
            f.write(f"{dir_name}:\n")
            f.write(f"  Total files: {len(all_files)}\n")
            f.write(f"  Included files: {len(included_files)}\n")
            f.write(f"  Excluded files: {len(excluded_files)}\n")
            f.write(f"  Dependencies: {', '.join(sorted(dependencies))}\n\n")
            all_dependencies.update(dependencies)
        f.write(f"All dependencies:\n{', '.join(sorted(all_dependencies))}\n")
    print(f"Summary has been written to: {summary_file}")

def combine_all_files(processed_dirs: Dict[str, Tuple[str, Tuple[List[str], List[str]], Set[str]]]):
    combined_file = os.path.join(OUTPUT_DIR, 'all_source_files_combined.txt')
    with open(combined_file, 'w', encoding='utf-8') as f:
        for dir_name, (dir_path, (included_files, excluded_files), _) in processed_dirs.items():
            f.write(f"// Files from {dir_name}:\n\n")
            for file in included_files:
                f.write(f"// {file}\n")
                try:
                    with open(os.path.join(dir_path, file), 'r', encoding='utf-8') as source_file:
                        f.write(source_file.read())
                except Exception as e:
                    f.write(f"// Error reading file: {str(e)}\n")
                f.write('\n\n')
    print(f"All source files have been combined into: {combined_file}")

def package_as_payload_plugin():
    plugin_dir = os.path.join(OUTPUT_DIR, 'payload-plugin')
    os.makedirs(plugin_dir, exist_ok=True)

    # Copy relevant files to the plugin directory
    for root, _, files in os.walk(OUTPUT_DIR):
        for file in files:
            if file.endswith('_source_files.txt') or file in ['summary.txt', 'all_source_files_combined.txt']:
                src_path = os.path.join(root, file)
                dst_path = os.path.join(plugin_dir, file)
                with open(src_path, 'r', encoding='utf-8') as src, open(dst_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())

    # Create a basic plugin structure
    with open(os.path.join(plugin_dir, 'index.js'), 'w', encoding='utf-8') as f:
        f.write("""
import { Plugin } from 'payload/config';

const TrelloCloudinaryPlugin: Plugin = {
  name: 'trello-cloudinary-plugin',
  // Add your plugin logic here
};

export default TrelloCloudinaryPlugin;
""")

    print(f"Payload CMS 3.0 Plugin package created in: {plugin_dir}")

if __name__ == '__main__':
    processed_dirs = {}

    # Process the entire project directory
    processed_dirs['project'] = process_directory('project', ROOT_DIR)

    generate_summary(processed_dirs)
    combine_all_files(processed_dirs)
    package_as_payload_plugin()
    print("Processing complete.")
