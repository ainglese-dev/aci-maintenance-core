# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ACI Maintenance Core is a professional multi-stage workflow toolkit for Cisco ACI fabric maintenance operations. The project has evolved from a single-file demo tool into a structured stage-based architecture designed for extensible maintenance workflows.

## Stage-Based Architecture

### Directory Structure
```
aci-maintenance-core/
├── stage1-inventory/          # Offline inventory generation
├── stage2-placeholder/        # Foundation for future comprehensive logic  
├── shared/                    # Common components across stages
└── aci-demo.py               # Legacy single-file tool (maintained for compatibility)
```
1
### Stage Philosophy
Each stage operates independently with clear input/output boundaries:
- **Stage 1**: Converts APIC GUI exports to Ansible inventory files
- **Stage 2**: Placeholder for future development (live data collection, validation, etc.)
- **Copy-Paste Workflow**: Simple file transfer between stages via outputs/ → inputs/ directories

### Shared Components
- `shared/rich_ui.py`: Professional TUI components with Rich library integration
- `shared/utils.py`: Common utilities for file handling, JSON parsing, inventory analysis

### Rich TUI with Graceful Fallback Pattern
```python
# Pattern used throughout codebase
try:
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

def rich_print(text, style=None, fallback_prefix=""):
    if RICH_AVAILABLE and console:
        console.print(text, style=style)
    else:
        print(f"{fallback_prefix}{text}")
```

### Data Processing Flow

1. **JSON Auto-Detection**: Scans current directory for `.json` files
2. **APIC Data Parsing**: Extracts fabric nodes from `imdata` → `fabricNode` structure
3. **Management IP Processing**: Handles both in-band (`mgmtRsInBStNode`) and out-of-band (`mgmtRsOoBStNode`) management
4. **User Interaction**: Interactive selection between management network types
5. **Inventory Generation**: Creates Ansible inventory with pod groupings and priorities

### Core Data Structures

**Node Object:**
```python
node = {
    'id': attrs.get('id', ''),
    'name': attrs.get('name', ''),
    'role': attrs.get('role', ''),  # controller, spine, leaf
    'model': attrs.get('model', ''),
    'serial': attrs.get('serial', ''),
    'podId': attrs.get('podId', '1'),
    'ip': None,  # Populated during IP merge
    'mgmt_type': None  # 'inband' or 'outband'
}
```

**Management IP Extraction:**
- Distinguished Name (DN) parsing to extract node IDs
- Separate tracking of in-band vs out-of-band IPs
- Preference-based selection with fallback logic

## Key Functions

### `extract_fabric_nodes(fabric_data)`
Parses APIC fabric membership JSON export. Expects `imdata` array containing `fabricNode` objects with `attributes` containing node metadata.

### `extract_management_ips(mgmt_data)`
Processes static node management JSON export. Returns separate dictionaries for in-band and out-of-band IPs plus user preference. Handles both management network types in single export.

### `merge_node_data(nodes, inband_ips, outband_ips, mgmt_preference)`
Merges fabric nodes with management IPs based on user preference. Implements fallback logic when preferred management type unavailable for specific nodes.

### `generate_ansible_inventory(nodes, mgmt_preference)`
Creates Ansible inventory file with:
- Pod-based groupings (`[apics_pod_1]`, `[spines_pod_1]`, etc.)
- Priority assignments for APIC controllers
- Node ID assignments for switches
- Management network type documentation in header

## Development Commands

### Stage 1 - Inventory Generation
```bash
cd stage1-inventory
cp sample-data/*.json .
python inventory-generator.py
```

### Stage 2 - Placeholder Processing  
```bash
cd stage2-placeholder
cp ../stage1-inventory/outputs/aci-inventory.ini inputs/
python stage2-tool.py
```

### Legacy Single-File Tool
```bash
# Original tool (maintained for compatibility)
python aci-demo.py
```

### Dependencies
```bash
pip install -r requirements.txt  # Only requires: rich>=13.0.0
```

## APIC JSON Export Requirements

**Fabric Membership Export:**
- Path: Fabric → Inventory → Fabric Membership → Export (JSON)
- Contains node roles, IDs, models, and pod assignments

**Static Node Management Export:**
- Path: Tenant mgmt → Static Node Management → Export (JSON)  
- Contains both in-band and out-of-band management IP assignments

## Sample Data Structure

The `sample-data/` directory contains realistic test data:
- Mixed in-band (172.16.1.x) and out-of-band (10.0.1.x) management IPs
- 9 nodes total: 3 APICs, 2 spines, 4 leaves
- Some nodes have both management types, others only one (realistic scenario)

## UI/UX Design Principles

- **60-second demo capability**: Tool designed for quick customer demonstrations
- **Auto-detection**: Minimal user input required, smart defaults
- **Professional presentation**: Rich tables, colored status messages, bordered panels
- **Management network visibility**: Clear indication of IP types and fallback usage
- **Graceful degradation**: Full functionality without Rich library installed

## Stage Development Guidelines

### Adding New Stages
1. Create `stageX-name/` directory with `inputs/`, `outputs/` subdirectories
2. Implement main script following naming pattern: `stageX-tool.py`
3. Create stage-specific README.md with usage instructions
4. Use shared components from `shared/` directory for consistency
5. Maintain copy-paste workflow: previous stage outputs → current stage inputs

### Code Stability Guidelines
- **Stage Isolation**: Each stage should be self-contained and independently testable
- **Rich/Fallback Pattern**: Maintain dual implementation throughout for graceful degradation
- **Auto-Detection**: Preserve intelligent file discovery and minimal user input
- **Professional UI**: Use shared Rich components for consistent presentation
- **60-Second Demo**: Ensure Stage 1 maintains rapid demonstration capability

### Shared Component Usage
- Import from `shared/rich_ui.py` for consistent TUI elements
- Use `shared/utils.py` for common file operations and data processing
- Maintain Rich graceful fallback pattern across all stages