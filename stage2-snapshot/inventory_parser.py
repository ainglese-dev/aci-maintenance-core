"""
Inventory parser for reading Stage 1 fabric discovery output
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import sys

# Add shared utilities to path
sys.path.append(str(Path(__file__).parent.parent / "shared"))
from device_info import DeviceInfo

logger = logging.getLogger(__name__)


@dataclass
class FabricInventory:
    """Container for parsed fabric inventory"""
    apic_devices: List[DeviceInfo]
    leaf_devices: List[DeviceInfo]
    spine_devices: List[DeviceInfo]
    other_devices: List[DeviceInfo]
    fabric_name: str
    discovery_timestamp: str
    total_devices: int


class InventoryParser:
    """Parse Stage 1 discovery output for Stage 2 data collection"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_stage1_output(self, stage1_path: str) -> Optional[FabricInventory]:
        """Parse Stage 1 discovery output file"""
        stage1_file = Path(stage1_path)
        
        if not stage1_file.exists():
            logger.error(f"Stage 1 output file not found: {stage1_path}")
            return None
        
        try:
            # Check if it's an INI file (from Stage 1) or JSON file
            if stage1_file.suffix.lower() == '.ini':
                return self.parse_ini_file(stage1_file)
            else:
                with open(stage1_file, 'r') as f:
                    stage1_data = json.load(f)
                
                logger.info(f"Loaded Stage 1 data from {stage1_file}")
                return self.parse_inventory_data(stage1_data)
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in Stage 1 file: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse Stage 1 file: {e}")
            return None
    
    def parse_ini_file(self, ini_file: Path) -> Optional[FabricInventory]:
        """Parse Ansible inventory INI file from Stage 1"""
        try:
            # Import here to avoid circular imports
            sys.path.append(str(Path(__file__).parent.parent / "shared"))
            from utils import read_inventory_file
            
            inventory_data = read_inventory_file(ini_file)
            if not inventory_data:
                logger.error(f"Failed to read inventory file: {ini_file}")
                return None
            
            # Convert INI data to FabricInventory format
            apic_devices = []
            leaf_devices = []
            spine_devices = []
            other_devices = []
            
            for host in inventory_data['hosts']:
                device_info = self.parse_ini_host(host)
                if device_info:
                    if 'apic' in host['section'].lower():
                        apic_devices.append(device_info)
                    elif 'leaf' in host['section'].lower() or 'leaves' in host['section'].lower():
                        leaf_devices.append(device_info)
                    elif 'spine' in host['section'].lower():
                        spine_devices.append(device_info)
                    else:
                        other_devices.append(device_info)
            
            # Extract metadata
            fabric_name = "ACI Fabric"
            discovery_timestamp = inventory_data.get('metadata', {}).get('generated', 'unknown')
            
            total_devices = len(apic_devices) + len(leaf_devices) + len(spine_devices) + len(other_devices)
            
            inventory = FabricInventory(
                apic_devices=apic_devices,
                leaf_devices=leaf_devices,
                spine_devices=spine_devices,
                other_devices=other_devices,
                fabric_name=fabric_name,
                discovery_timestamp=discovery_timestamp,
                total_devices=total_devices
            )
            
            logger.info(f"Parsed INI inventory: {len(apic_devices)} APICs, {len(leaf_devices)} LEAFs, "
                       f"{len(spine_devices)} SPINEs, {len(other_devices)} other devices")
            
            return inventory
            
        except Exception as e:
            logger.error(f"Failed to parse INI file {ini_file}: {e}")
            return None
    
    def parse_ini_host(self, host_data: Dict[str, Any]) -> Optional[DeviceInfo]:
        """Parse a single host from INI file"""
        try:
            # Extract hostname/IP from the line
            line = host_data['line']
            parts = line.split()
            hostname = parts[0]
            
            # Parse additional parameters
            params = {}
            for part in parts[1:]:
                if '=' in part:
                    key, value = part.split('=', 1)
                    params[key] = value
            
            # Determine device type from section
            section = host_data['section'].lower()
            if 'apic' in section:
                device_type = 'apic'
            elif 'leaf' in section or 'leaves' in section:
                device_type = 'leaf'
            elif 'spine' in section:
                device_type = 'spine'
            else:
                device_type = 'other'
            
            # Extract node ID and priority
            node_id = None
            priority = 1
            if 'node_id' in params:
                try:
                    node_id = int(params['node_id'])
                except ValueError:
                    pass
            if 'priority' in params:
                try:
                    priority = int(params['priority'])
                except ValueError:
                    pass
            
            device_info = DeviceInfo(
                name=hostname,
                hostname=hostname,
                device_type=device_type,
                node_id=node_id,
                priority=priority
            )
            
            return device_info
            
        except Exception as e:
            logger.warning(f"Failed to parse host entry: {e}")
            return None
    
    def parse_inventory_data(self, data: Dict[str, Any]) -> FabricInventory:
        """Parse inventory data into device categories"""
        
        # Extract metadata
        fabric_name = data.get('fabric_name', 'unknown')
        discovery_timestamp = data.get('discovery_timestamp', 'unknown')
        
        # Parse device lists
        apic_devices = self.parse_device_list(data.get('apic_devices', []), 'apic')
        leaf_devices = self.parse_device_list(data.get('leaf_devices', []), 'leaf')
        spine_devices = self.parse_device_list(data.get('spine_devices', []), 'spine')
        other_devices = self.parse_device_list(data.get('other_devices', []), 'other')
        
        total_devices = len(apic_devices) + len(leaf_devices) + len(spine_devices) + len(other_devices)
        
        inventory = FabricInventory(
            apic_devices=apic_devices,
            leaf_devices=leaf_devices,
            spine_devices=spine_devices,
            other_devices=other_devices,
            fabric_name=fabric_name,
            discovery_timestamp=discovery_timestamp,
            total_devices=total_devices
        )
        
        logger.info(f"Parsed inventory: {len(apic_devices)} APICs, {len(leaf_devices)} LEAFs, "
                   f"{len(spine_devices)} SPINEs, {len(other_devices)} other devices")
        
        return inventory
    
    def parse_device_list(self, device_list: List[Dict], device_type: str) -> List[DeviceInfo]:
        """Parse list of devices into DeviceInfo objects"""
        devices = []
        
        for device_data in device_list:
            try:
                device_info = DeviceInfo(
                    name=device_data.get('name', 'unknown'),
                    hostname=device_data.get('hostname', device_data.get('ip', 'unknown')),
                    username=device_data.get('username', ''),
                    password=device_data.get('password', ''),
                    device_type=device_type,
                    node_id=device_data.get('node_id'),
                    priority=device_data.get('priority', 1),
                    port=device_data.get('port', 22 if device_type != 'apic' else 443)
                )
                devices.append(device_info)
                
            except Exception as e:
                logger.warning(f"Failed to parse device {device_data.get('name', 'unknown')}: {e}")
                continue
        
        return devices
    
    def find_stage1_output(self, search_paths: List[str] = None) -> Optional[str]:
        """Find the most recent Stage 1 output file"""
        if not search_paths:
            search_paths = [
                "inputs/aci-inventory.ini",
                "../stage1-inventory/outputs/aci-inventory.ini",
                "./aci-inventory.ini",
                "../aci-inventory.ini"
            ]
        
        for search_path in search_paths:
            path = Path(search_path)
            if path.exists():
                logger.info(f"Found Stage 1 output: {path}")
                return str(path.absolute())
        
        logger.warning("No Stage 1 output file found in default locations")
        return None
    
    def validate_inventory(self, inventory: FabricInventory) -> bool:
        """Validate that inventory has minimum required devices"""
        validation_errors = []
        
        # Must have at least one APIC
        if len(inventory.apic_devices) == 0:
            validation_errors.append("No APIC controllers found")
        
        # Must have at least one leaf or spine
        if len(inventory.leaf_devices) == 0 and len(inventory.spine_devices) == 0:
            validation_errors.append("No leaf or spine switches found")
        
        # Check for reasonable fabric size
        if inventory.total_devices < 2:
            validation_errors.append(f"Very small fabric: only {inventory.total_devices} devices")
        
        # Check device connectivity requirements
        for apic in inventory.apic_devices:
            if not apic.hostname or apic.hostname == 'unknown':
                validation_errors.append(f"APIC {apic.name} missing hostname/IP")
        
        if validation_errors:
            logger.error("Inventory validation failed:")
            for error in validation_errors:
                logger.error(f"  - {error}")
            return False
        
        logger.info("✓ Inventory validation passed")
        return True
    
    def get_collection_targets(self, inventory: FabricInventory) -> Dict[str, List[DeviceInfo]]:
        """Get organized collection targets for different collector types"""
        return {
            'fabric': inventory.apic_devices,  # Fabric-wide collection via APIC
            'apic': inventory.apic_devices,    # APIC-specific collection
            'leaf': inventory.leaf_devices,    # Leaf switch collection
            'spine': inventory.spine_devices   # Spine switch collection
        }
    
    def create_collection_summary(self, inventory: FabricInventory) -> str:
        """Create human-readable summary of collection targets"""
        summary = []
        summary.append(f"FABRIC INVENTORY SUMMARY")
        summary.append("=" * 50)
        summary.append(f"Fabric Name: {inventory.fabric_name}")
        summary.append(f"Discovered: {inventory.discovery_timestamp}")
        summary.append(f"Total Devices: {inventory.total_devices}")
        summary.append("")
        
        summary.append("COLLECTION TARGETS:")
        summary.append(f"  APIC Controllers: {len(inventory.apic_devices)}")
        for apic in inventory.apic_devices:
            summary.append(f"    - {apic.name} ({apic.hostname})")
        
        summary.append(f"  Leaf Switches: {len(inventory.leaf_devices)}")
        for leaf in inventory.leaf_devices[:5]:  # Show first 5
            summary.append(f"    - {leaf.name} ({leaf.hostname})")
        if len(inventory.leaf_devices) > 5:
            summary.append(f"    ... and {len(inventory.leaf_devices) - 5} more")
        
        summary.append(f"  Spine Switches: {len(inventory.spine_devices)}")
        for spine in inventory.spine_devices[:5]:  # Show first 5
            summary.append(f"    - {spine.name} ({spine.hostname})")
        if len(inventory.spine_devices) > 5:
            summary.append(f"    ... and {len(inventory.spine_devices) - 5} more")
        
        if inventory.other_devices:
            summary.append(f"  Other Devices: {len(inventory.other_devices)}")
        
        return "\n".join(summary)


def load_inventory_from_stage1(stage1_path: str = None) -> Optional[FabricInventory]:
    """Convenience function to load inventory from Stage 1 output"""
    parser = InventoryParser()
    
    if not stage1_path:
        stage1_path = parser.find_stage1_output()
        if not stage1_path:
            logger.error("Could not find Stage 1 output file")
            return None
    
    inventory = parser.parse_stage1_output(stage1_path)
    if not inventory:
        return None
    
    if not parser.validate_inventory(inventory):
        logger.error("Inventory validation failed")
        return None
    
    return inventory


if __name__ == "__main__":
    # Test the parser
    logging.basicConfig(level=logging.INFO)
    
    inventory = load_inventory_from_stage1()
    if inventory:
        parser = InventoryParser()
        print(parser.create_collection_summary(inventory))
    else:
        print("Failed to load inventory")