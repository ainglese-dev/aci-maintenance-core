# APIC moquery Commands for ACI Maintenance Core

This document provides the exact moquery commands needed to gather JSON files for the ACI Maintenance Core tool from the APIC CLI.

## Overview

The ACI Maintenance Core tool requires two main JSON files to generate Ansible inventory files:
1. **Fabric Inventory** - Information about all fabric nodes (APICs, spines, leaves)
2. **Management IP Assignments** - Static management IP configurations

## Required moquery Commands

### 1. Fabric Inventory Export

**Command:**
```bash
moquery -c fabricNode -o json > fabric_inventory.json
```

**What it does:**
- Queries all fabric nodes in the ACI fabric
- Exports data in JSON format to `fabric_inventory.json`
- Includes APICs, spine switches, and leaf switches

**Expected data structure:**
```json
{
  "imdata": [
    {
      "fabricNode": {
        "attributes": {
          "id": "1",
          "name": "apic1",
          "role": "controller",
          "fabricSt": "active",
          "model": "APIC-M3",
          "serial": "FDO24261234",
          "version": "5.2(4e)",
          "podId": "1",
          "dn": "topology/pod-1/node-1"
        }
      }
    }
  ],
  "totalCount": "9"
}
```

### 2. Management IP Assignments Export

**Command:**
```bash
moquery -c mgmtRsInBStNode,mgmtRsOoBStNode -o json > management_ips.json
```

**What it does:**
- Queries both in-band and out-of-band management IP assignments
- Exports data in JSON format to `management_ips.json`
- Captures all static node management configurations

**Expected data structure:**
```json
{
  "imdata": [
    {
      "mgmtRsOoBStNode": {
        "attributes": {
          "tDn": "topology/pod-1/node-1",
          "addr": "10.0.1.11",
          "gw": "10.0.1.1",
          "dn": "uni/tn-mgmt/mgmtp-default/oob-default/rsooBStNode-[topology/pod-1/node-1]"
        }
      }
    },
    {
      "mgmtRsInBStNode": {
        "attributes": {
          "tDn": "topology/pod-1/node-101",
          "addr": "172.16.1.101",
          "gw": "172.16.1.1",
          "dn": "uni/tn-mgmt/mgmtp-default/inb-default/rsinBStNode-[topology/pod-1/node-101]"
        }
      }
    }
  ],
  "totalCount": "12"
}
```

## Alternative Commands (if combined query fails)

If the combined management IP query doesn't work, use these separate commands:

### In-band Management IPs Only
```bash
moquery -c mgmtRsInBStNode -o json > inband_mgmt.json
```

### Out-of-band Management IPs Only  
```bash
moquery -c mgmtRsOoBStNode -o json > outband_mgmt.json
```

**Note:** If using separate files, you'll need to manually combine them or modify the tool to handle multiple management files.

## Step-by-Step Process

### On APIC CLI:
1. SSH to any APIC in the fabric
2. Run the moquery commands above
3. Transfer the JSON files to your workstation

### On Windows/Linux Workstation:
1. Place the JSON files in the `stage1-inventory/` directory
2. Run the inventory generator:
   ```bash
   cd stage1-inventory
   python inventory-generator.py
   ```

## File Naming Requirements

The inventory generator auto-detects JSON files, but these names are recommended:
- `fabric_inventory.json` - Fabric node information
- `management_ips.json` - Management IP assignments
- `apic_controllers.json` - Alternative name for fabric inventory
- Any `.json` files in the directory will be processed

## Data Validation

The tool validates that JSON files contain:
- `imdata` array at the root level
- Proper `fabricNode` objects with required attributes
- Valid management IP relationship objects
- Consistent node references between files

## Common Issues and Solutions

### Issue: "No fabric nodes found"
**Solution:** Ensure your `fabric_inventory.json` contains `fabricNode` objects in the `imdata` array.

### Issue: "No management IPs found"
**Solution:** Check that management IP assignments exist in the fabric and are properly exported.

### Issue: "Node ID mismatch"
**Solution:** Verify that node IDs in management IPs match the topology references from fabric inventory.

### Issue: "Empty JSON files"
**Solution:** Ensure you have read permissions for the managed objects in APIC.

## Advanced Usage

### Filtering by Pod
```bash
# Only nodes in pod 1
moquery -c fabricNode -f 'fabric.Node.podId=="1"' -o json > pod1_inventory.json
```

### Specific Node Types
```bash
# Only leaf nodes
moquery -c fabricNode -f 'fabric.Node.role=="leaf"' -o json > leaf_nodes.json

# Only spine nodes  
moquery -c fabricNode -f 'fabric.Node.role=="spine"' -o json > spine_nodes.json
```

### Including Additional Attributes
```bash
# With additional node details
moquery -c fabricNode -x rsp-prop-include=config-only -o json > detailed_inventory.json
```

## Verification Commands

### Check fabric node count
```bash
moquery -c fabricNode -o count
```

### Check management IP assignments
```bash
moquery -c mgmtRsInBStNode -o count
moquery -c mgmtRsOoBStNode -o count
```

### Validate specific node
```bash
moquery -c fabricNode -f 'fabric.Node.name=="leaf1"' -o json
```

## Integration with ACI Maintenance Core

Once you have the correct JSON files:

1. **Stage 1 - Inventory Generation:**
   ```bash
   cd stage1-inventory
   cp /path/to/your/fabric_inventory.json .
   cp /path/to/your/management_ips.json .
   python inventory-generator.py
   ```

2. **Stage 2 - Snapshot Collection:**
   ```bash
   cd stage2-snapshot
   cp ../stage1-inventory/outputs/aci-inventory.ini inputs/
   python stage2-collector.py collect --baseline
   ```

The moquery commands provided here will generate JSON files that are 100% compatible with the ACI Maintenance Core tool's expected data structures.