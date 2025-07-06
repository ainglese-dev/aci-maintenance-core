"""
Leaf switch data collector using NX-OS CLI commands
"""

import logging
import re
from typing import Dict, List, Any, Optional
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)


class LeafCollector(BaseCollector):
    """Collects leaf-specific data via NX-OS CLI"""
    
    # NX-OS commands for leaf switches
    LEAF_COMMANDS = {
        'interfaces': {
            'command': 'show interface status',
            'description': 'Interface status and configuration'
        },
        'port_channels': {
            'command': 'show port-channel summary',
            'description': 'Port channel status and members'
        },
        'mac_table': {
            'command': 'show mac address-table',
            'description': 'MAC address table entries'
        },
        'arp_table': {
            'command': 'show ip arp vrf all',
            'description': 'ARP table entries for all VRFs'
        },
        'vlans': {
            'command': 'show vlan brief',
            'description': 'VLAN configuration and status'
        },
        'vpc': {
            'command': 'show vpc brief',
            'description': 'vPC status and configuration'
        },
        'fabric_interfaces': {
            'command': 'show interface fabric brief',
            'description': 'Fabric interface status'
        },
        'endpoints': {
            'command': 'show system internal epm endpoint summary',
            'description': 'Endpoint database summary'
        },
        'bridge_domains': {
            'command': 'show system internal epm bd summary',
            'description': 'Bridge domain endpoint summary'
        }
    }
    
    def __init__(self):
        super().__init__("LeafCollector")
        
    def collect(self, fabric_client, device_info) -> Dict[str, Any]:
        """Collect leaf switch data via NX-OS CLI"""
        self.start_collection()
        
        # Connect to leaf switch
        nxos_client = fabric_client.connect_to_device(device_info)
        if not nxos_client:
            self.add_error(f"Failed to connect to leaf {device_info.name}")
            return self.end_collection({})
        
        leaf_data = {
            'device_info': {
                'name': device_info.name,
                'hostname': device_info.hostname,
                'node_id': device_info.node_id,
                'device_type': device_info.device_type
            }
        }
        
        # Execute commands
        commands_to_run = [cmd_config['command'] for cmd_config in self.LEAF_COMMANDS.values()]
        results = nxos_client.execute_commands(commands_to_run)
        
        # Process command outputs
        for data_type, cmd_config in self.LEAF_COMMANDS.items():
            command = cmd_config['command']
            
            if command in results and results[command]:
                try:
                    processed_data = self.process_command_output(data_type, results[command])
                    leaf_data[data_type] = {
                        'command': command,
                        'description': cmd_config['description'],
                        'raw_output': results[command],
                        'processed_data': processed_data
                    }
                    logger.info(f"✓ Processed {data_type} data from {device_info.name}")
                except Exception as e:
                    self.add_error(f"Failed to process {data_type} on {device_info.name}: {str(e)}")
                    leaf_data[data_type] = {
                        'command': command,
                        'description': cmd_config['description'],
                        'raw_output': results[command],
                        'error': str(e)
                    }
            else:
                self.add_error(f"No output for {data_type} command on {device_info.name}")
                leaf_data[data_type] = {
                    'command': command,
                    'description': cmd_config['description'],
                    'error': 'No command output'
                }
        
        # Validate collected data
        self.validate_leaf_data(leaf_data, device_info)
        
        return self.end_collection(leaf_data)
    
    def process_command_output(self, data_type: str, raw_output: str) -> Dict[str, Any]:
        """Process raw command output into structured data"""
        
        if data_type == 'interfaces':
            return self.parse_interface_status(raw_output)
        elif data_type == 'port_channels':
            return self.parse_port_channel_summary(raw_output)
        elif data_type == 'mac_table':
            return self.parse_mac_table(raw_output)
        elif data_type == 'arp_table':
            return self.parse_arp_table(raw_output)
        elif data_type == 'vlans':
            return self.parse_vlan_brief(raw_output)
        elif data_type == 'vpc':
            return self.parse_vpc_brief(raw_output)
        elif data_type == 'fabric_interfaces':
            return self.parse_fabric_interfaces(raw_output)
        elif data_type == 'endpoints':
            return self.parse_endpoint_summary(raw_output)
        elif data_type == 'bridge_domains':
            return self.parse_bd_summary(raw_output)
        else:
            # Default: return line count and sample
            lines = raw_output.strip().split('\n')
            return {
                'line_count': len(lines),
                'sample_lines': lines[:5] if lines else []
            }
    
    def parse_interface_status(self, output: str) -> Dict[str, Any]:
        """Parse 'show interface status' output"""
        interfaces = []
        lines = output.strip().split('\n')
        
        # Skip header lines
        data_lines = [line for line in lines if not line.startswith('Port') and not line.startswith('----')]
        
        for line in data_lines:
            if line.strip():
                # Basic parsing - can be enhanced based on exact output format
                parts = line.split()
                if len(parts) >= 4:
                    interfaces.append({
                        'interface': parts[0],
                        'status': parts[1] if len(parts) > 1 else 'unknown',
                        'vlan': parts[2] if len(parts) > 2 else 'unknown',
                        'duplex': parts[3] if len(parts) > 3 else 'unknown'
                    })
        
        return {
            'total_interfaces': len(interfaces),
            'up_interfaces': len([i for i in interfaces if 'connected' in i.get('status', '').lower()]),
            'interfaces': interfaces
        }
    
    def parse_port_channel_summary(self, output: str) -> Dict[str, Any]:
        """Parse 'show port-channel summary' output"""
        port_channels = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if 'Po' in line and ('(SU)' in line or '(SD)' in line):
                parts = line.split()
                if len(parts) >= 2:
                    port_channels.append({
                        'interface': parts[0],
                        'status': 'up' if '(SU)' in line else 'down',
                        'protocol': parts[1] if len(parts) > 1 else 'unknown'
                    })
        
        return {
            'total_port_channels': len(port_channels),
            'up_port_channels': len([pc for pc in port_channels if pc['status'] == 'up']),
            'port_channels': port_channels
        }
    
    def parse_mac_table(self, output: str) -> Dict[str, Any]:
        """Parse 'show mac address-table' output"""
        lines = output.strip().split('\n')
        mac_count = 0
        
        for line in lines:
            if re.search(r'[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}', line):
                mac_count += 1
        
        return {
            'total_mac_entries': mac_count,
            'raw_line_count': len(lines)
        }
    
    def parse_arp_table(self, output: str) -> Dict[str, Any]:
        """Parse 'show ip arp vrf all' output"""
        lines = output.strip().split('\n')
        arp_count = 0
        
        for line in lines:
            if re.search(r'\d+\.\d+\.\d+\.\d+', line) and 'incomplete' not in line.lower():
                arp_count += 1
        
        return {
            'total_arp_entries': arp_count,
            'raw_line_count': len(lines)
        }
    
    def parse_vlan_brief(self, output: str) -> Dict[str, Any]:
        """Parse 'show vlan brief' output"""
        lines = output.strip().split('\n')
        vlan_count = 0
        
        for line in lines:
            if re.search(r'^\s*\d+', line):
                vlan_count += 1
        
        return {
            'total_vlans': vlan_count,
            'raw_line_count': len(lines)
        }
    
    def parse_vpc_brief(self, output: str) -> Dict[str, Any]:
        """Parse 'show vpc brief' output"""
        vpc_enabled = 'vPC domain id' in output
        vpc_status = 'up' if 'vPC status' in output and 'up' in output else 'down'
        
        return {
            'vpc_enabled': vpc_enabled,
            'vpc_status': vpc_status if vpc_enabled else 'disabled'
        }
    
    def parse_fabric_interfaces(self, output: str) -> Dict[str, Any]:
        """Parse 'show interface fabric brief' output"""
        lines = output.strip().split('\n')
        fabric_interfaces = []
        
        for line in lines:
            if 'Fabric' in line or 'fabric' in line:
                fabric_interfaces.append(line.strip())
        
        return {
            'total_fabric_interfaces': len(fabric_interfaces),
            'fabric_interfaces': fabric_interfaces
        }
    
    def parse_endpoint_summary(self, output: str) -> Dict[str, Any]:
        """Parse endpoint summary output"""
        lines = output.strip().split('\n')
        
        # Look for total endpoint count
        total_endpoints = 0
        for line in lines:
            if 'Total' in line and 'endpoint' in line.lower():
                numbers = re.findall(r'\d+', line)
                if numbers:
                    total_endpoints = int(numbers[-1])
                break
        
        return {
            'total_endpoints': total_endpoints,
            'raw_line_count': len(lines)
        }
    
    def parse_bd_summary(self, output: str) -> Dict[str, Any]:
        """Parse bridge domain summary output"""
        lines = output.strip().split('\n')
        
        return {
            'bridge_domain_count': max(0, len(lines) - 5),  # Rough estimate
            'raw_line_count': len(lines)
        }
    
    def validate_leaf_data(self, data: Dict[str, Any], device_info):
        """Validate leaf data completeness"""
        critical_collections = ['interfaces', 'fabric_interfaces']
        
        for collection in critical_collections:
            if collection not in data or 'error' in data[collection]:
                self.add_error(f"Critical: Failed to collect {collection} from {device_info.name}")
        
        # Check for reasonable interface counts
        if 'interfaces' in data and 'processed_data' in data['interfaces']:
            interface_data = data['interfaces']['processed_data']
            total_interfaces = interface_data.get('total_interfaces', 0)
            
            if total_interfaces == 0:
                self.add_error(f"Warning: No interfaces found on {device_info.name}")
            elif total_interfaces > 100:
                logger.warning(f"Large interface count on {device_info.name}: {total_interfaces}")
        
        return len(self.errors) == 0