"""
Common utilities for ACI Maintenance stages
"""

import json
import os
from pathlib import Path
from datetime import datetime


def load_json_file(filepath):
    """Load and parse JSON file"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None


def find_files(directory, pattern="*"):
    """Find files matching pattern in directory"""
    directory = Path(directory)
    if not directory.exists():
        return []
    return list(directory.glob(pattern))


def create_timestamped_filename(base_name, extension=""):
    """Create filename with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if extension and not extension.startswith('.'):
        extension = f".{extension}"
    return f"{base_name}_{timestamp}{extension}"


def ensure_directory(directory):
    """Ensure directory exists, create if not"""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def read_inventory_file(filepath):
    """Read and parse Ansible inventory file"""
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        inventory_data = {
            'sections': [],
            'hosts': [],
            'metadata': {}
        }
        
        current_section = None
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                # Parse metadata from comments
                if 'Generated:' in line:
                    inventory_data['metadata']['generated'] = line.split('Generated:')[1].strip()
                elif 'Management Network:' in line:
                    inventory_data['metadata']['management_type'] = line.split('Management Network:')[1].strip()
            elif line.startswith('[') and ']' in line:
                # Section header
                current_section = line.strip('[]')
                inventory_data['sections'].append(current_section)
            elif line and not line.startswith('[') and '=' in line:
                # Host entry
                host_name = line.split()[0]
                inventory_data['hosts'].append({
                    'name': host_name,
                    'section': current_section,
                    'line': line
                })
        
        return inventory_data
    except Exception as e:
        print(f"Error reading inventory file {filepath}: {e}")
        return None


def get_stage_info():
    """Get current stage information based on working directory"""
    cwd = Path.cwd()
    if 'stage1-inventory' in str(cwd):
        return {'stage': 1, 'name': 'Inventory Generation', 'dir': 'stage1-inventory'}
    elif 'stage2-placeholder' in str(cwd):
        return {'stage': 2, 'name': 'Placeholder Stage', 'dir': 'stage2-placeholder'}
    else:
        return {'stage': 0, 'name': 'Main Directory', 'dir': '.'}