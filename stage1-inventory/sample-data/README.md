# Sample Data Files

These are example JSON exports from APIC GUI for testing the demo tool.

## Files

- **fabric_inventory.json** - Example fabric membership export
- **management_ips.json** - Example static node management export  
- **apic_controllers.json** - Example APIC controllers export (optional)

## Usage

```bash
# Copy sample files to main directory
cp sample-data/*.json .

# Run demo tool
python aci-demo.py
```

The tool will auto-detect these files and generate an Ansible inventory.