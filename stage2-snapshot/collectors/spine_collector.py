"""
Spine switch data collector using NX-OS CLI commands
"""

import logging
import re
from typing import Dict, List, Any, Optional
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)


class SpineCollector(BaseCollector):
    """Collects spine-specific data via NX-OS CLI"""
    
    # NX-OS commands for spine switches
    SPINE_COMMANDS = {
        'fabric_interfaces': {
            'command': 'show interface fabric brief',
            'description': 'Fabric interface status to all leafs'
        },
        'isis_neighbors': {
            'command': 'show isis adjacency',
            'description': 'IS-IS adjacency database'
        },
        'isis_database': {
            'command': 'show isis database',
            'description': 'IS-IS topology database'
        },
        'ospf_neighbors': {
            'command': 'show ip ospf neighbors',
            'description': 'OSPF neighbor status'
        },
        'ospf_database': {
            'command': 'show ip ospf database',
            'description': 'OSPF topology database'
        },
        'bgp_summary': {
            'command': 'show ip bgp summary',
            'description': 'BGP neighbor summary'
        },
        'bgp_evpn_summary': {
            'command': 'show bgp l2vpn evpn summary',
            'description': 'BGP EVPN neighbor summary'
        },
        'nve_peers': {
            'command': 'show nve peers',
            'description': 'NVE peer status'
        },
        'multicast_routes': {
            'command': 'show ip mroute summary',
            'description': 'Multicast routing table summary'
        },
        'interface_counters': {
            'command': 'show interface counters',
            'description': 'Interface packet/byte counters'
        },
        'fabric_multicast': {
            'command': 'show fabric multicast globals',
            'description': 'Fabric multicast configuration'
        }
    }
    
    def __init__(self):
        super().__init__("SpineCollector")
        
    def collect(self, fabric_client, device_info) -> Dict[str, Any]:
        """Collect spine switch data via NX-OS CLI"""
        self.start_collection()
        
        # Connect to spine switch
        nxos_client = fabric_client.connect_to_device(device_info)
        if not nxos_client:
            self.add_error(f"Failed to connect to spine {device_info.name}")
            return self.end_collection({})
        
        spine_data = {
            'device_info': {
                'name': device_info.name,
                'hostname': device_info.hostname,
                'node_id': device_info.node_id,
                'device_type': device_info.device_type
            }
        }
        
        # Execute commands
        commands_to_run = [cmd_config['command'] for cmd_config in self.SPINE_COMMANDS.values()]
        results = nxos_client.execute_commands(commands_to_run)
        
        # Process command outputs
        for data_type, cmd_config in self.SPINE_COMMANDS.items():
            command = cmd_config['command']
            
            if command in results and results[command]:
                try:
                    processed_data = self.process_command_output(data_type, results[command])
                    spine_data[data_type] = {
                        'command': command,
                        'description': cmd_config['description'],
                        'raw_output': results[command],
                        'processed_data': processed_data
                    }
                    logger.info(f"✓ Processed {data_type} data from {device_info.name}")
                except Exception as e:
                    self.add_error(f"Failed to process {data_type} on {device_info.name}: {str(e)}")
                    spine_data[data_type] = {
                        'command': command,
                        'description': cmd_config['description'],
                        'raw_output': results[command],
                        'error': str(e)
                    }
            else:
                self.add_error(f"No output for {data_type} command on {device_info.name}")
                spine_data[data_type] = {
                    'command': command,
                    'description': cmd_config['description'],
                    'error': 'No command output'
                }
        
        # Validate collected data
        self.validate_spine_data(spine_data, device_info)
        
        return self.end_collection(spine_data)
    
    def process_command_output(self, data_type: str, raw_output: str) -> Dict[str, Any]:
        """Process raw command output into structured data"""
        
        if data_type == 'fabric_interfaces':
            return self.parse_fabric_interfaces(raw_output)
        elif data_type == 'isis_neighbors':
            return self.parse_isis_neighbors(raw_output)
        elif data_type == 'isis_database':
            return self.parse_isis_database(raw_output)
        elif data_type == 'ospf_neighbors':
            return self.parse_ospf_neighbors(raw_output)
        elif data_type == 'ospf_database':
            return self.parse_ospf_database(raw_output)
        elif data_type == 'bgp_summary':
            return self.parse_bgp_summary(raw_output)
        elif data_type == 'bgp_evpn_summary':
            return self.parse_bgp_evpn_summary(raw_output)
        elif data_type == 'nve_peers':
            return self.parse_nve_peers(raw_output)
        elif data_type == 'multicast_routes':
            return self.parse_multicast_routes(raw_output)
        elif data_type == 'interface_counters':
            return self.parse_interface_counters(raw_output)
        elif data_type == 'fabric_multicast':
            return self.parse_fabric_multicast(raw_output)
        else:
            # Default: return line count and sample
            lines = raw_output.strip().split('\n')
            return {
                'line_count': len(lines),
                'sample_lines': lines[:5] if lines else []
            }
    
    def parse_fabric_interfaces(self, output: str) -> Dict[str, Any]:
        """Parse fabric interface status"""
        lines = output.strip().split('\n')
        fabric_interfaces = []
        up_count = 0
        
        for line in lines:
            if 'Fabric' in line or 'fabric' in line:
                fabric_interfaces.append(line.strip())
                if 'up' in line.lower():
                    up_count += 1
        
        return {
            'total_fabric_interfaces': len(fabric_interfaces),
            'up_fabric_interfaces': up_count,
            'down_fabric_interfaces': len(fabric_interfaces) - up_count,
            'interfaces': fabric_interfaces
        }
    
    def parse_isis_neighbors(self, output: str) -> Dict[str, Any]:
        """Parse IS-IS adjacency information"""
        lines = output.strip().split('\n')
        neighbors = []
        up_neighbors = 0
        
        for line in lines:
            if re.search(r'\d+\.\d+\.\d+\.\d+', line) or 'Level' in line:
                neighbors.append(line.strip())
                if 'UP' in line.upper():
                    up_neighbors += 1
        
        return {
            'total_isis_neighbors': len(neighbors),
            'up_isis_neighbors': up_neighbors,
            'down_isis_neighbors': len(neighbors) - up_neighbors,
            'neighbors': neighbors
        }
    
    def parse_isis_database(self, output: str) -> Dict[str, Any]:
        """Parse IS-IS database information"""
        lines = output.strip().split('\n')
        lsp_count = 0
        
        for line in lines:
            if re.search(r'\d+\.\d+\.\d+\.\d+-\d+', line):
                lsp_count += 1
        
        return {
            'total_lsp_entries': lsp_count,
            'database_line_count': len(lines)
        }
    
    def parse_ospf_neighbors(self, output: str) -> Dict[str, Any]:
        """Parse OSPF neighbor information"""
        lines = output.strip().split('\n')
        neighbors = []
        full_neighbors = 0
        
        for line in lines:
            if re.search(r'\d+\.\d+\.\d+\.\d+', line):
                neighbors.append(line.strip())
                if 'FULL' in line.upper():
                    full_neighbors += 1
        
        return {
            'total_ospf_neighbors': len(neighbors),
            'full_ospf_neighbors': full_neighbors,
            'not_full_neighbors': len(neighbors) - full_neighbors,
            'neighbors': neighbors
        }
    
    def parse_ospf_database(self, output: str) -> Dict[str, Any]:
        """Parse OSPF database information"""
        lines = output.strip().split('\n')
        lsa_count = 0
        
        for line in lines:
            if re.search(r'\d+\.\d+\.\d+\.\d+', line) and ('Router' in line or 'Network' in line):
                lsa_count += 1
        
        return {
            'total_lsa_entries': lsa_count,
            'database_line_count': len(lines)
        }
    
    def parse_bgp_summary(self, output: str) -> Dict[str, Any]:
        """Parse BGP summary information"""
        lines = output.strip().split('\n')
        neighbors = []
        established_neighbors = 0
        
        for line in lines:
            if re.search(r'\d+\.\d+\.\d+\.\d+', line):
                neighbors.append(line.strip())
                # Look for established state (usually indicated by uptime or established status)
                if re.search(r'\d+:\d+:\d+|\d+w\d+d|\d+d\d+h|Established', line):
                    established_neighbors += 1
        
        return {
            'total_bgp_neighbors': len(neighbors),
            'established_bgp_neighbors': established_neighbors,
            'down_bgp_neighbors': len(neighbors) - established_neighbors,
            'neighbors': neighbors
        }
    
    def parse_bgp_evpn_summary(self, output: str) -> Dict[str, Any]:
        """Parse BGP EVPN summary information"""
        lines = output.strip().split('\n')
        evpn_neighbors = []
        established_evpn = 0
        
        for line in lines:
            if re.search(r'\d+\.\d+\.\d+\.\d+', line):
                evpn_neighbors.append(line.strip())
                if re.search(r'\d+:\d+:\d+|\d+w\d+d|\d+d\d+h|Established', line):
                    established_evpn += 1
        
        return {
            'total_evpn_neighbors': len(evpn_neighbors),
            'established_evpn_neighbors': established_evpn,
            'down_evpn_neighbors': len(evpn_neighbors) - established_evpn,
            'neighbors': evpn_neighbors
        }
    
    def parse_nve_peers(self, output: str) -> Dict[str, Any]:
        """Parse NVE peer information"""
        lines = output.strip().split('\n')
        peers = []
        up_peers = 0
        
        for line in lines:
            if re.search(r'\d+\.\d+\.\d+\.\d+', line):
                peers.append(line.strip())
                if 'UP' in line.upper():
                    up_peers += 1
        
        return {
            'total_nve_peers': len(peers),
            'up_nve_peers': up_peers,
            'down_nve_peers': len(peers) - up_peers,
            'peers': peers
        }
    
    def parse_multicast_routes(self, output: str) -> Dict[str, Any]:
        """Parse multicast routing summary"""
        lines = output.strip().split('\n')
        
        # Look for route counts in summary
        total_routes = 0
        for line in lines:
            if 'Total' in line and 'route' in line.lower():
                numbers = re.findall(r'\d+', line)
                if numbers:
                    total_routes = int(numbers[-1])
                break
        
        return {
            'total_mcast_routes': total_routes,
            'summary_line_count': len(lines)
        }
    
    def parse_interface_counters(self, output: str) -> Dict[str, Any]:
        """Parse interface counters"""
        lines = output.strip().split('\n')
        interface_count = 0
        
        for line in lines:
            if re.search(r'^Eth\d+/\d+|^Po\d+', line):
                interface_count += 1
        
        return {
            'interfaces_with_counters': interface_count,
            'counter_line_count': len(lines)
        }
    
    def parse_fabric_multicast(self, output: str) -> Dict[str, Any]:
        """Parse fabric multicast globals"""
        lines = output.strip().split('\n')
        
        multicast_enabled = any('enable' in line.lower() for line in lines)
        
        return {
            'multicast_enabled': multicast_enabled,
            'config_line_count': len(lines)
        }
    
    def validate_spine_data(self, data: Dict[str, Any], device_info):
        """Validate spine data completeness"""
        critical_collections = ['fabric_interfaces', 'bgp_summary', 'bgp_evpn_summary']
        
        for collection in critical_collections:
            if collection not in data or 'error' in data[collection]:
                self.add_error(f"Critical: Failed to collect {collection} from {device_info.name}")
        
        # Check for reasonable neighbor counts
        if 'bgp_summary' in data and 'processed_data' in data['bgp_summary']:
            bgp_data = data['bgp_summary']['processed_data']
            total_neighbors = bgp_data.get('total_bgp_neighbors', 0)
            established = bgp_data.get('established_bgp_neighbors', 0)
            
            if total_neighbors == 0:
                self.add_error(f"Warning: No BGP neighbors found on spine {device_info.name}")
            elif established < total_neighbors:
                self.add_error(f"Warning: {total_neighbors - established} BGP neighbors down on {device_info.name}")
        
        # Check fabric interface health
        if 'fabric_interfaces' in data and 'processed_data' in data['fabric_interfaces']:
            fabric_data = data['fabric_interfaces']['processed_data']
            total_fabric = fabric_data.get('total_fabric_interfaces', 0)
            down_fabric = fabric_data.get('down_fabric_interfaces', 0)
            
            if total_fabric == 0:
                self.add_error(f"Critical: No fabric interfaces found on spine {device_info.name}")
            elif down_fabric > 0:
                self.add_error(f"Warning: {down_fabric} fabric interfaces down on {device_info.name}")
        
        return len(self.errors) == 0