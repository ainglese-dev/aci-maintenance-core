# Stage 2: ACI Fabric Data Collector

## Purpose
Pure data collection from live ACI fabric and switches. No analysis or comparison - just gather raw fabric state and store as timestamped snapshots.

## Input
- `inputs/aci-inventory.ini` - Fabric inventory from Stage 1

## Process
1. Parse inventory to identify APIC controllers and switches
2. Connect to APIC for fabric-wide data collection
3. Connect to individual switches for device-specific data
4. Store all collected data as timestamped JSON snapshots

## Output
- `outputs/snapshots/YYYYMMDD_HHMMSS_fabric_snapshot.json` - Complete fabric state

## Usage
```bash
cd stage2-collector
python stage2-collector.py collect --username admin --password <password>
```

## Data Collected
- APIC system information and health
- Fabric topology and node status
- Switch hardware inventory
- Interface status and statistics
- Fault and health information
- Policy configuration summaries

## Requirements
- Live network connectivity to ACI fabric
- Valid APIC credentials
- Inventory file from Stage 1