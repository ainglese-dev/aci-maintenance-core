# Stage 2: ACI Fabric Snapshot Collector

A comprehensive data collection and comparison tool for Cisco ACI fabric maintenance windows. This tool captures fabric-wide and device-specific data before and after maintenance activities to validate fabric health and detect changes.

## Features

- **Fabric-wide Data Collection**: Topology, links, faults, health scores via APIC REST API
- **Device-specific Collection**: 
  - **LEAF**: Edge interfaces, endpoint tables, VLANs, fabric connectivity
  - **SPINE**: Fabric interfaces, underlay protocols (OSPF/ISIS), overlay protocols (BGP/EVPN)
  - **APIC**: Cluster health, policy status, firmware versions
- **Snapshot Management**: Timestamped storage with human-readable summaries
- **Comparison Engine**: Baseline vs current snapshot analysis
- **Error Detection**: Automatic validation and health assessment

## Prerequisites

1. **Stage 1 Discovery**: Must be run first to generate fabric inventory
2. **Python Dependencies**: Install with `pip install -r ../requirements.txt`
3. **Network Access**: SSH access to switches, HTTPS access to APIC
4. **Credentials**: APIC username/password with read permissions

## Quick Start

### 1. Collect Baseline Snapshot (Pre-maintenance)
```bash
# Collect comprehensive baseline before maintenance
./stage2-collector.py collect --baseline --username admin

# Or with custom name
./stage2-collector.py collect --snapshot-name "pre-maintenance-2024-01-06"
```

### 2. Collect Current Snapshot (Post-maintenance)
```bash
# Collect after maintenance for comparison
./stage2-collector.py collect --snapshot-name "post-maintenance"
```

### 3. Compare Snapshots
```bash
# Compare baseline vs current
./stage2-collector.py compare \
  --baseline-snapshot snapshots/baseline_20240106_143022 \
  --current-snapshot snapshots/post-maintenance \
  --show-report
```

### 4. List Available Snapshots
```bash
./stage2-collector.py list
```

## Command Reference

### Collection Modes

- `collect`: Gather fabric data into timestamped snapshot
- `compare`: Generate comparison report between two snapshots  
- `list`: Show available snapshots

### Collection Options

- `--baseline`: Mark snapshot as baseline (adds timestamp prefix)
- `--snapshot-name`: Custom snapshot name
- `--inventory-file`: Stage 1 inventory file (auto-detected if not specified)
- `--username/--password`: APIC credentials
- `--skip-fabric/--skip-apic/--skip-leaf/--skip-spine`: Skip specific collection types

### Comparison Options

- `--baseline-snapshot`: Path to baseline snapshot directory
- `--current-snapshot`: Path to current snapshot directory  
- `--show-report`: Display comparison report after generation

## Data Collection Details

### APIC REST API Endpoints (Fabric & APIC)
- `/api/class/fabricNode.json` - Fabric topology
- `/api/class/fabricLink.json` - Inter-node links
- `/api/class/faultInst.json` - System faults
- `/api/class/healthInst.json` - Health scores
- `/api/class/infraWiNode.json` - APIC cluster status
- `/api/class/infraCluster.json` - Cluster state
- `/api/class/firmwareRunning.json` - Firmware versions

### NX-OS CLI Commands (LEAF/SPINE)

**LEAF Switches:**
- `show interface status` - Edge interface status
- `show mac address-table` - Endpoint learning
- `show ip arp vrf all` - ARP table
- `show vlan brief` - VLAN configuration
- `show vpc brief` - vPC status
- `show interface fabric brief` - Fabric connectivity

**SPINE Switches:**  
- `show interface fabric brief` - Fabric interface matrix
- `show isis adjacency` - IS-IS underlay
- `show ip ospf neighbors` - OSPF underlay
- `show ip bgp summary` - BGP overlay
- `show bgp l2vpn evpn summary` - EVPN overlay
- `show nve peers` - VXLAN tunnels

## Snapshot Structure

```
snapshots/
├── baseline_20240106_143022/
│   ├── fabric_data.json           # Raw APIC data
│   ├── fabric_summary.txt         # Human-readable summary
│   ├── apic_data.json            # APIC-specific data
│   ├── apic_summary.txt
│   ├── leaf_switch1_data.json    # Per-device data
│   ├── leaf_switch1_summary.txt
│   ├── spine_switch1_data.json
│   ├── spine_switch1_summary.txt
│   └── snapshot_summary.txt      # Overall health assessment
└── post-maintenance/
    └── [same structure]

comparisons/
└── comparison_report_20240106_150022.txt
```

## Health Assessment

Each snapshot includes automatic health assessment:

- **🟢 HEALTHY**: All collections successful, no critical issues
- **🟡 WARNING**: Minor issues detected (1-3 errors)  
- **🔴 CRITICAL**: Multiple issues requiring investigation

## Error Handling

- **Connection Failures**: Graceful degradation, continues with available devices
- **Command Failures**: Individual command errors don't stop collection
- **Data Validation**: Automatic validation of critical collection types
- **Comprehensive Logging**: Debug information for troubleshooting

## Integration with Stage 1

Stage 2 automatically reads the fabric inventory generated by Stage 1:
- Device lists (APIC, LEAF, SPINE)
- Connection details (hostnames, credentials)
- Node IDs and device types
- Priority ordering for APIC failover

## Maintenance Window Workflow

1. **Pre-maintenance**: `./stage2-collector.py collect --baseline`
2. **Perform maintenance activities**
3. **Post-maintenance**: `./stage2-collector.py collect --snapshot-name "post-maintenance"`  
4. **Validation**: `./stage2-collector.py compare --baseline-snapshot <baseline> --current-snapshot <current>`
5. **Review**: Check comparison report for unexpected changes

## Troubleshooting

### Common Issues

**"No Stage 1 output file found"**
- Run Stage 1 discovery first
- Verify `discovered_fabric.json` exists in parent directory

**"Failed to connect to fabric"**
- Check APIC connectivity and credentials
- Verify Stage 1 discovered correct APIC IPs
- Check firewall/network access

**"Critical: Failed to collect fabric_interfaces"**
- Verify SSH access to switches
- Check NX-OS CLI command permissions
- Review device credentials in Stage 1 output

### Debug Mode
```bash
./stage2-collector.py collect --verbose --log-file debug.log
```

### Partial Collection
```bash
# Skip problematic device types
./stage2-collector.py collect --skip-spine --skip-leaf
```

## Advanced Usage

### Custom Inventory File
```bash
./stage2-collector.py collect --inventory-file /path/to/custom_inventory.json
```

### Scheduled Collection
```bash
# Cron job for baseline collection
0 2 * * 0 cd /path/to/aci-maintenance-core/stage2-snapshot && ./stage2-collector.py collect --baseline
```

### Integration with CI/CD
```bash
# Exit code 0 on success, 1 on failure
./stage2-collector.py collect --baseline
if [ $? -eq 0 ]; then
    echo "Baseline collection successful"
else
    echo "Baseline collection failed"
    exit 1
fi
```