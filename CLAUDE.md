# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ACI Maintenance Core is a professional multi-stage workflow toolkit for Cisco ACI fabric maintenance operations. The project has evolved from a single-file demo tool into a structured stage-based architecture designed for extensible maintenance workflows.

## Quick Setup for New Computer

### Prerequisites
- Python 3.8+ installed
- Git installed  
- Network access to ACI fabric
- Valid APIC credentials

### Environment Setup
```bash
# 1. Clone repository
git clone <repository-url>
cd aci-maintenance-core

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Verify installation
python stage2-collector/stage2-collector.py --help
```

### Network Requirements
- **APIC HTTPS Access**: Port 443 to APIC management IP
- **SSH Access** (optional): Port 22 to individual switches
- **Certificate Handling**: APIC uses self-signed certificates (verification disabled by default)
- **Firewall**: Ensure outbound HTTPS (443) is allowed to APIC subnet

### Configuration Setup
Create configuration file for secure credential handling:

```bash
# Create config directory
mkdir -p stage2-collector/config

# Create configuration file
cat > stage2-collector/config/fabric.json << EOF
{
    "fabric_name": "Production ACI",
    "apic": {
        "username": "admin",
        "password": "your-password-here",
        "verify_ssl": false
    },
    "collection": {
        "timeout": 30,
        "parallel_collections": true,
        "retry_attempts": 3
    }
}
EOF
```

### Quick Test
```bash
# Test connectivity to APIC (without credentials)
cd stage2-collector
python stage2-collector.py test --apic-ip 10.66.93.16

# Test with credentials
python stage2-collector.py test --config config/fabric.json

# Run first collection
python stage2-collector.py collect --config config/fabric.json
```

## Stage-Based Architecture

### Directory Structure
```
aci-maintenance-core/
├── stage1-inventory/          # Offline inventory generation
├── stage2-collector/          # Live fabric data collection
├── stage3-analyzer/           # Offline data analysis and comparison
├── stage2-snapshot/           # Legacy combined collector (deprecated)  
├── shared/                    # Common components across stages
└── aci-demo.py               # Legacy single-file tool (maintained for compatibility)
```

### Stage Philosophy
Each stage operates independently with clear input/output boundaries:
- **Stage 1**: Converts APIC GUI exports to Ansible inventory files (offline)
- **Stage 2**: Connects to live fabric and collects raw data snapshots (online)
- **Stage 3**: Analyzes collected snapshots and generates comparison reports (offline)
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

### Stage 2 - Data Collection (Live Fabric)
```bash
cd stage2-collector
cp ../stage1-inventory/outputs/aci-inventory.ini inputs/

# Option 1: Using configuration file (recommended)
python stage2-collector.py collect --config config/fabric.json

# Option 2: Using command line (less secure)
python stage2-collector.py collect --username admin --password <password>

# Option 3: Using environment variables
export ACI_USERNAME=admin
export ACI_PASSWORD=<password>
python stage2-collector.py collect
```

### Stage 3 - Data Analysis (Offline)
```bash
cd stage3-analyzer
cp ../stage2-collector/outputs/snapshots/*.json inputs/snapshots/
python stage3-tool.py list
python stage3-tool.py compare --before snapshot1.json --after snapshot2.json
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

## Testing & Validation Framework

### Connectivity Testing
Test APIC reachability and basic connectivity without full data collection:

```bash
cd stage2-collector

# Test network connectivity to APIC
python stage2-collector.py test --apic-ip 10.66.93.16

# Test APIC authentication
python stage2-collector.py test --config config/fabric.json

# Test specific fabric components
python stage2-collector.py test --config config/fabric.json --test-fabric
```

### Inventory Validation
Validate Stage 1 inventory before collection:

```bash
cd stage2-collector

# Validate inventory file format
python stage2-collector.py validate --inventory inputs/aci-inventory.ini

# Check inventory devices are reachable
python stage2-collector.py validate --inventory inputs/aci-inventory.ini --check-connectivity
```

### Mock Collection Mode
Test collection logic without live fabric access:

```bash
cd stage2-collector

# Run collection in mock mode (uses sample responses)
python stage2-collector.py collect --mock --config config/fabric.json

# Validate mock data structure
python stage2-collector.py validate --snapshot outputs/snapshots/mock_snapshot.json
```

### End-to-End Workflow Testing
Complete workflow validation:

```bash
# 1. Generate inventory from sample data
cd stage1-inventory
python inventory-generator.py

# 2. Test Stage 2 connectivity
cd ../stage2-collector
cp ../stage1-inventory/outputs/aci-inventory.ini inputs/
python stage2-collector.py test --config config/fabric.json

# 3. Run collection
python stage2-collector.py collect --config config/fabric.json

# 4. Validate snapshot
python stage2-collector.py validate --snapshot outputs/snapshots/latest.json

# 5. Test Stage 3 analysis
cd ../stage3-analyzer
cp ../stage2-collector/outputs/snapshots/*.json inputs/snapshots/
python stage3-tool.py list
```

### Troubleshooting Commands
Common diagnostic commands:

```bash
# Check Python environment
python --version
pip list | grep rich

# Test APIC connectivity manually
curl -k https://10.66.93.16/api/aaaLogin.json -X POST \
  -H "Content-Type: application/json" \
  -d '{"aaaUser":{"attributes":{"name":"admin","pwd":"password"}}}'

# Check file permissions and paths
ls -la stage2-collector/inputs/
ls -la stage2-collector/outputs/snapshots/

# Enable verbose logging
python stage2-collector.py collect --config config/fabric.json --verbose
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

## Production Deployment Features

### Configuration Management
Production deployments should use configuration files instead of command-line credentials:

**Example Production Config** (`stage2-collector/config/production.json`):
```json
{
    "fabric_name": "Production ACI DC1",
    "apic": {
        "username": "service-account",
        "password": "${ACI_PASSWORD}",
        "verify_ssl": false,
        "timeout": 30
    },
    "collection": {
        "parallel_collections": true,
        "retry_attempts": 3,
        "collection_timeout": 300,
        "max_concurrent_devices": 10
    },
    "logging": {
        "level": "INFO",
        "file": "logs/stage2-collector.log",
        "max_size_mb": 100,
        "backup_count": 5
    },
    "storage": {
        "snapshot_retention_days": 30,
        "compression": true
    }
}
```

### Environment Variables Support
For secure credential management:
```bash
export ACI_PASSWORD="secure-password"
export ACI_LOG_LEVEL="DEBUG"
export ACI_TIMEOUT="60"

# Configuration can reference environment variables
python stage2-collector.py collect --config config/production.json
```

### Logging and Monitoring
```bash
# Create logs directory
mkdir -p stage2-collector/logs

# Run with structured logging
python stage2-collector.py collect --config config/production.json --log-file logs/collection.log

# Monitor collection progress
tail -f logs/collection.log

# Check collection metrics
python stage2-collector.py status --last-collection
```

### Performance Optimization
For large fabrics:
```bash
# Parallel collection with progress monitoring
python stage2-collector.py collect \
  --config config/production.json \
  --parallel \
  --progress \
  --timeout 300

# Collection with device filtering
python stage2-collector.py collect \
  --config config/production.json \
  --devices "apic,spine" \
  --exclude-leaves
```

### Data Management
```bash
# List snapshots with metadata
python stage2-collector.py snapshots --list --details

# Cleanup old snapshots (keep last 30 days)
python stage2-collector.py snapshots --cleanup --retention-days 30

# Export snapshot for analysis
python stage2-collector.py snapshots --export snapshot_20250707.json --format csv

# Validate snapshot integrity
python stage2-collector.py validate --snapshot snapshot_20250707.json --full-check
```

### Scheduling and Automation
Production collection scheduling:
```bash
# Crontab example - collect every 4 hours
0 */4 * * * cd /opt/aci-maintenance-core/stage2-collector && ./collect.sh >> logs/cron.log 2>&1

# collect.sh script example:
#!/bin/bash
source ../venv/bin/activate
python stage2-collector.py collect --config config/production.json --quiet
if [ $? -eq 0 ]; then
    echo "$(date): Collection successful"
else
    echo "$(date): Collection failed" >&2
    exit 1
fi
```

### Security Considerations
- Store credentials in environment variables, not configuration files
- Use dedicated service accounts with minimal required permissions
- Enable audit logging for all APIC API calls
- Regularly rotate service account passwords
- Consider certificate-based authentication for production

### Backup and Recovery
```bash
# Backup configuration and data
tar -czf aci-backup-$(date +%Y%m%d).tar.gz \
  stage2-collector/config/ \
  stage2-collector/outputs/snapshots/ \
  stage3-analyzer/outputs/reports/

# Restore from backup
tar -xzf aci-backup-20250707.tar.gz
```

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

## Complete Workflow Example

### First-Time Setup on New Computer
```bash
# 1. Clone and setup environment
git clone <repository-url>
cd aci-maintenance-core
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Create configuration
mkdir -p stage2-collector/config
cat > stage2-collector/config/lab.json << EOF
{
    "fabric_name": "Lab ACI",
    "apic": {
        "username": "admin",
        "password": "${ACI_PASSWORD}",
        "verify_ssl": false
    }
}
EOF

# 3. Set credentials securely
export ACI_PASSWORD="your-lab-password"

# 4. Test connectivity
cd stage2-collector
python stage2-collector.py test --apic-ip 10.66.93.16
```

### Daily Collection Workflow
```bash
# 1. Activate environment
source venv/bin/activate
export ACI_PASSWORD="your-password"

# 2. Generate fresh inventory (if APIC exports updated)
cd stage1-inventory
cp sample-data/*.json .  # or use real exports
python inventory-generator.py

# 3. Run data collection
cd ../stage2-collector
cp ../stage1-inventory/outputs/aci-inventory.ini inputs/
python stage2-collector.py collect --config config/lab.json

# 4. Analyze results
cd ../stage3-analyzer
cp ../stage2-collector/outputs/snapshots/*.json inputs/snapshots/
python stage3-tool.py list
```

### Before/After Maintenance Comparison
```bash
# Before maintenance
cd stage2-collector
python stage2-collector.py collect --config config/lab.json --label "pre-maintenance"

# After maintenance  
python stage2-collector.py collect --config config/lab.json --label "post-maintenance"

# Generate comparison report
cd ../stage3-analyzer
cp ../stage2-collector/outputs/snapshots/*pre-maintenance*.json inputs/snapshots/
cp ../stage2-collector/outputs/snapshots/*post-maintenance*.json inputs/snapshots/
python stage3-tool.py compare --before pre-maintenance.json --after post-maintenance.json
```

### Troubleshooting Quick Reference
```bash
# Check environment
python --version && pip list | grep rich

# Test APIC connectivity
curl -k https://10.66.93.16/api/class/topSystem.json

# Validate inventory
cd stage2-collector
python stage2-collector.py validate --inventory inputs/aci-inventory.ini

# Run in verbose mode
python stage2-collector.py collect --config config/lab.json --verbose

# Check logs
tail -f logs/stage2-collector.log
```

This documentation is now ready for deployment on another computer with ACI fabric access!