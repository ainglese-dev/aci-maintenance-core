# ACI Maintenance Core

Professional multi-stage workflow toolkit for Cisco ACI fabric maintenance operations.

## Overview

This toolkit provides a stage-based approach to ACI maintenance with clear separation of concerns:

- **Stage 1**: Generate Ansible inventory from APIC GUI exports  
- **Stage 2**: Future comprehensive maintenance logic (placeholder)
- **Shared Components**: Common utilities and Rich TUI components

## Quick Start

### Single Tool Usage (Legacy)

```bash
# Use original single-file tool
python aci-demo.py
```

### Stage-Based Workflow (Recommended)

```bash
# Stage 1: Generate inventory
cd stage1-inventory
cp sample-data/*.json .
python inventory-generator.py

# Stage 2: Process inventory (placeholder)
cp outputs/aci-inventory.ini ../stage2-placeholder/inputs/
cd ../stage2-placeholder
python stage2-tool.py
```

## Stage Structure

```
aci-maintenance-core/
├── stage1-inventory/          # Offline inventory generation
│   ├── inventory-generator.py # Convert APIC exports to Ansible inventory
│   ├── sample-data/          # Test data from APIC GUI
│   └── outputs/              # Generated inventory files
├── stage2-placeholder/        # Foundation for future logic
│   ├── stage2-tool.py        # Placeholder processing tool
│   ├── inputs/               # Copy files from previous stage
│   └── outputs/              # Stage 2 results
├── shared/                    # Common components
│   ├── rich_ui.py            # Professional TUI components
│   └── utils.py              # Shared utilities
└── aci-demo.py               # Original single-file tool
```

## Dependencies

```bash
pip install -r requirements.txt
```

Only requires: `rich>=13.0.0` (with graceful fallback if unavailable)

## Key Features

- **Professional TUI**: Rich library integration with colored tables and panels
- **Management Network Choice**: Interactive in-band vs out-of-band IP selection
- **Auto-Detection**: Intelligent JSON file discovery and processing
- **Stage Isolation**: Clear input/output separation between workflow stages
- **Copy-Paste Workflow**: Simple file transfer between stages
- **Extensible Design**: Easy to add new stages for complex workflows

## APIC Data Collection

**Stage 1 requires JSON files with fabric and management data:**

### GUI Export Method (Original)
1. **Fabric Membership**: Fabric → Inventory → Fabric Membership → Export (JSON)
2. **Static Node Management**: Tenant mgmt → Static Node Management → Export (JSON)

### CLI moquery Method (Recommended)
```bash
# From APIC CLI - get fabric nodes
moquery -c fabricNode -o json > fabric_inventory.json

# Get management IP assignments  
moquery -c mgmtRsInBStNode,mgmtRsOoBStNode -o json > management_ips.json
```

📖 **Complete CLI reference: [MOQUERY_COMMANDS.md](MOQUERY_COMMANDS.md)**

## Development

Each stage is independent with its own:
- Input/output directories
- Documentation (README.md)
- Specific functionality
- Clear workflow integration points

See individual stage README files for detailed usage instructions.

## Architecture

Built for customer demonstrations and proof-of-concept scenarios with:
- 60-second demo capability
- Professional presentation
- Extensible multi-stage design
- Minimal dependencies
- Graceful fallback support