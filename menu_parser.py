#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import sys
import os
import json

def get_directory_name(dir_path):
    """Read the directory file and extract the Name value."""
    try:
        with open(dir_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('Name='):
                    return line.strip().split('=', 1)[1]
    except Exception as e:
        print(f"  Error reading directory file {dir_path}: {e}", file=sys.stderr)
    return None

def get_desktop_info(file_path):
    """Read the .desktop file and extract the Name, Exec, and Icon values."""
    name = None
    exec_cmd = None
    icon = None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('Name='):
                    name = line.strip().split('=', 1)[1]
                elif line.startswith('Exec='):
                    exec_cmd = line.strip().split('=', 1)[1]
                elif line.startswith('Icon='):
                    icon = line.strip().split('=', 1)[1]
    except Exception as e:
        print(f"  Error reading desktop file {file_path}: {e}", file=sys.stderr)
    return name, exec_cmd, icon

def clean_filename(filename):
    """Remove the 'thinlinc-' prefix from the filename."""
    if filename.startswith('thinlinc-'):
        return filename[9:]  # Remove 'thinlinc-' prefix
    return filename

def parse_menu_file(file_path):
    """Parse the applications.menu file and extract menu entries."""
    menu_structure = {}
    
    try:
        # Parse the XML file
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Base directory prefix
        base_dir = "/opt/thinlinc/desktops/xdg_data_dir/directories"
        app_dir = "/opt/thinlinc/desktops/xdg_data_dir/applications/thinlinc"
        
        def process_menu(menu_elem, parent_dir=None):
            """Process a menu element and its children recursively."""
            dir_elem = menu_elem.find('Directory')
            if dir_elem is not None:
                dir_path = f"{base_dir}/{dir_elem.text}"
                dir_name = get_directory_name(dir_path)
                if dir_name:
                    if dir_name not in menu_structure:
                        menu_structure[dir_name] = []
                    
                    # Process Include section
                    include_elem = menu_elem.find('Include')
                    if include_elem is not None:
                        for filename in include_elem.findall('Filename'):
                            clean_name = clean_filename(filename.text)
                            desktop_path = f"{app_dir}/{clean_name}"
                            desktop_name, exec_cmd, icon = get_desktop_info(desktop_path)
                            if desktop_name:
                                app_info = {"name": desktop_name}
                                if exec_cmd:
                                    app_info["exec"] = exec_cmd
                                if icon:
                                    app_info["icon"] = icon
                                menu_structure[dir_name].append(app_info)
            
            # Process submenus
            for submenu in menu_elem.findall('.//Menu'):
                process_menu(submenu, dir_name)
        
        # Process all top-level menus
        for menu in root.findall('.//Menu'):
            process_menu(menu)
        
        # Write the JSON output to a file
        output_file = "menu_structure.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(menu_structure, f, indent=2, ensure_ascii=False)
        
        print(f"Menu structure has been written to {output_file}")

    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    file_path = "/N/u/henschel/Quartz/.config/menus/applications.menu"
    parse_menu_file(file_path)

if __name__ == "__main__":
    main() 