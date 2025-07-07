"""
APIC controller data collector using REST API
"""

import logging
from typing import Dict, List, Any, Optional
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)


class ApicCollector(BaseCollector):
    """Collects APIC-specific data via REST API"""
    
    # APIC REST API endpoints for controller-specific data
    APIC_ENDPOINTS = {
        'cluster_health': {
            'endpoint': '/api/class/infraWiNode.json',
            'description': 'APIC cluster node status'
        },
        'cluster_state': {
            'endpoint': '/api/class/infraCluster.json',
            'description': 'APIC cluster state information'
        },
        'policy_usage': {
            'endpoint': '/api/class/polUni.json',
            'params': {'query-target': 'children'},
            'description': 'Policy universe configuration'
        },
        'fabric_membership': {
            'endpoint': '/api/class/fabricNodeIdentPol.json',
            'description': 'Fabric node identity policies'
        },
        'discovery_issues': {
            'endpoint': '/api/class/fabricNodeBlk.json',
            'description': 'Fabric node discovery blocks'
        },
        'system_faults': {
            'endpoint': '/api/class/faultInst.json',
            'params': {'query-target-filter': 'and(eq(faultInst.severity,"critical"),eq(faultInst.type,"operational"))'},
            'description': 'Critical operational faults'
        },
        'capacity_dashboard': {
            'endpoint': '/api/class/eqptcapacityEntity.json',
            'description': 'Equipment capacity information'
        },
        'firmware_status': {
            'endpoint': '/api/class/firmwareRunning.json',
            'description': 'Running firmware versions'
        },
        'license_usage': {
            'endpoint': '/api/class/licenseEntitlement.json',
            'description': 'License entitlement status'
        },
        'backup_policy': {
            'endpoint': '/api/class/configBackupPol.json',
            'description': 'Configuration backup policies'
        }
    }
    
    def __init__(self):
        super().__init__("ApicCollector")
        
    def collect(self, fabric_client) -> Dict[str, Any]:
        """Collect APIC controller data via REST API"""
        self.start_collection()
        
        apic_data = {}
        
        for data_type, config in self.APIC_ENDPOINTS.items():
            try:
                logger.info(f"Collecting {data_type}: {config['description']}")
                
                params = config.get('params', None)
                response = fabric_client.get_fabric_data(config['endpoint'], params)
                
                if response and 'imdata' in response:
                    processed_data = self.process_apic_data(data_type, response['imdata'])
                    apic_data[data_type] = {
                        'endpoint': config['endpoint'],
                        'description': config['description'],
                        'count': len(response['imdata']),
                        'data': response['imdata'],
                        'processed_data': processed_data
                    }
                    logger.info(f"✓ Collected {len(response['imdata'])} {data_type} records")
                else:
                    self.add_error(f"No data returned for {data_type}")
                    apic_data[data_type] = {
                        'endpoint': config['endpoint'],
                        'description': config['description'],
                        'count': 0,
                        'data': [],
                        'processed_data': {}
                    }
                    
            except Exception as e:
                self.add_error(f"Failed to collect {data_type}: {str(e)}")
                apic_data[data_type] = {
                    'endpoint': config['endpoint'],
                    'description': config['description'],
                    'count': 0,
                    'data': [],
                    'error': str(e),
                    'processed_data': {}
                }
        
        # Validate collected data
        self.validate_apic_data(apic_data)
        
        return self.end_collection(apic_data)
    
    def process_apic_data(self, data_type: str, raw_data: List[Dict]) -> Dict[str, Any]:
        """Process raw APIC data into structured information"""
        
        if data_type == 'cluster_health':
            return self.process_cluster_health(raw_data)
        elif data_type == 'cluster_state':
            return self.process_cluster_state(raw_data)
        elif data_type == 'policy_usage':
            return self.process_policy_usage(raw_data)
        elif data_type == 'fabric_membership':
            return self.process_fabric_membership(raw_data)
        elif data_type == 'discovery_issues':
            return self.process_discovery_issues(raw_data)
        elif data_type == 'system_faults':
            return self.process_system_faults(raw_data)
        elif data_type == 'capacity_dashboard':
            return self.process_capacity_dashboard(raw_data)
        elif data_type == 'firmware_status':
            return self.process_firmware_status(raw_data)
        elif data_type == 'license_usage':
            return self.process_license_usage(raw_data)
        elif data_type == 'backup_policy':
            return self.process_backup_policy(raw_data)
        else:
            return {'raw_count': len(raw_data)}
    
    def process_cluster_health(self, data: List[Dict]) -> Dict[str, Any]:
        """Process APIC cluster health information"""
        cluster_nodes = []
        healthy_nodes = 0
        
        for item in data:
            if 'infraWiNode' in item:
                attrs = item['infraWiNode']['attributes']
                node_info = {
                    'id': attrs.get('id', 'unknown'),
                    'name': attrs.get('name', 'unknown'),
                    'health': attrs.get('health', 'unknown'),
                    'state': attrs.get('state', 'unknown')
                }
                cluster_nodes.append(node_info)
                
                if attrs.get('health') == 'fully-fit':
                    healthy_nodes += 1
        
        return {
            'total_cluster_nodes': len(cluster_nodes),
            'healthy_nodes': healthy_nodes,
            'unhealthy_nodes': len(cluster_nodes) - healthy_nodes,
            'nodes': cluster_nodes
        }
    
    def process_cluster_state(self, data: List[Dict]) -> Dict[str, Any]:
        """Process APIC cluster state information"""
        cluster_info = {}
        
        for item in data:
            if 'infraCluster' in item:
                attrs = item['infraCluster']['attributes']
                cluster_info = {
                    'cluster_size': attrs.get('size', 'unknown'),
                    'quorum_status': attrs.get('quorum', 'unknown'),
                    'leader_id': attrs.get('leader', 'unknown')
                }
                break
        
        return cluster_info
    
    def process_policy_usage(self, data: List[Dict]) -> Dict[str, Any]:
        """Process policy configuration usage"""
        policy_count = len(data)
        policy_types = {}
        
        for item in data:
            for policy_type in item.keys():
                if policy_type in policy_types:
                    policy_types[policy_type] += 1
                else:
                    policy_types[policy_type] = 1
        
        return {
            'total_policies': policy_count,
            'policy_types_count': len(policy_types),
            'policy_breakdown': policy_types
        }
    
    def process_fabric_membership(self, data: List[Dict]) -> Dict[str, Any]:
        """Process fabric node membership policies"""
        node_policies = []
        
        for item in data:
            if 'fabricNodeIdentPol' in item:
                attrs = item['fabricNodeIdentPol']['attributes']
                node_policies.append({
                    'name': attrs.get('name', 'unknown'),
                    'serial': attrs.get('serial', 'unknown'),
                    'node_id': attrs.get('nodeId', 'unknown')
                })
        
        return {
            'total_node_policies': len(node_policies),
            'node_policies': node_policies
        }
    
    def process_discovery_issues(self, data: List[Dict]) -> Dict[str, Any]:
        """Process fabric discovery issues"""
        discovery_blocks = []
        
        for item in data:
            if 'fabricNodeBlk' in item:
                attrs = item['fabricNodeBlk']['attributes']
                discovery_blocks.append({
                    'from_node': attrs.get('from_', 'unknown'),
                    'to_node': attrs.get('to_', 'unknown'),
                    'name': attrs.get('name', 'unknown')
                })
        
        return {
            'total_discovery_blocks': len(discovery_blocks),
            'discovery_blocks': discovery_blocks
        }
    
    def process_system_faults(self, data: List[Dict]) -> Dict[str, Any]:
        """Process critical system faults"""
        critical_faults = []
        
        for item in data:
            if 'faultInst' in item:
                attrs = item['faultInst']['attributes']
                critical_faults.append({
                    'code': attrs.get('code', 'unknown'),
                    'description': attrs.get('descr', 'unknown'),
                    'severity': attrs.get('severity', 'unknown'),
                    'dn': attrs.get('dn', 'unknown')
                })
        
        return {
            'total_critical_faults': len(critical_faults),
            'critical_faults': critical_faults
        }
    
    def process_capacity_dashboard(self, data: List[Dict]) -> Dict[str, Any]:
        """Process equipment capacity information"""
        capacity_info = {
            'total_capacity_entities': len(data),
            'capacity_details': []
        }
        
        for item in data:
            if 'eqptcapacityEntity' in item:
                attrs = item['eqptcapacityEntity']['attributes']
                capacity_info['capacity_details'].append({
                    'dn': attrs.get('dn', 'unknown'),
                    'current': attrs.get('current', 'unknown'),
                    'maximum': attrs.get('maximum', 'unknown')
                })
        
        return capacity_info
    
    def process_firmware_status(self, data: List[Dict]) -> Dict[str, Any]:
        """Process firmware version information"""
        firmware_versions = {}
        
        for item in data:
            if 'firmwareRunning' in item:
                attrs = item['firmwareRunning']['attributes']
                version = attrs.get('version', 'unknown')
                
                if version in firmware_versions:
                    firmware_versions[version] += 1
                else:
                    firmware_versions[version] = 1
        
        return {
            'total_firmware_entries': len(data),
            'unique_versions': len(firmware_versions),
            'version_distribution': firmware_versions
        }
    
    def process_license_usage(self, data: List[Dict]) -> Dict[str, Any]:
        """Process license entitlement information"""
        license_info = []
        
        for item in data:
            if 'licenseEntitlement' in item:
                attrs = item['licenseEntitlement']['attributes']
                license_info.append({
                    'feature': attrs.get('feature', 'unknown'),
                    'count': attrs.get('count', 'unknown'),
                    'state': attrs.get('state', 'unknown')
                })
        
        return {
            'total_license_entitlements': len(license_info),
            'license_details': license_info
        }
    
    def process_backup_policy(self, data: List[Dict]) -> Dict[str, Any]:
        """Process backup policy configuration"""
        backup_policies = []
        
        for item in data:
            if 'configBackupPol' in item:
                attrs = item['configBackupPol']['attributes']
                backup_policies.append({
                    'name': attrs.get('name', 'unknown'),
                    'admin_state': attrs.get('adminSt', 'unknown'),
                    'format': attrs.get('format', 'unknown')
                })
        
        return {
            'total_backup_policies': len(backup_policies),
            'backup_policies': backup_policies
        }
    
    def validate_apic_data(self, data: Dict[str, Any]):
        """Validate APIC data completeness and health"""
        critical_collections = ['cluster_health', 'cluster_state', 'system_faults']
        
        for collection in critical_collections:
            if collection not in data or 'error' in data[collection]:
                self.add_error(f"Critical: Failed to collect {collection}")
        
        # Check cluster health
        if 'cluster_health' in data and 'processed_data' in data['cluster_health']:
            cluster_data = data['cluster_health']['processed_data']
            unhealthy_nodes = cluster_data.get('unhealthy_nodes', 0)
            
            if unhealthy_nodes > 0:
                self.add_error(f"Warning: {unhealthy_nodes} APIC cluster nodes are unhealthy")
        
        # Check for critical faults
        if 'system_faults' in data and 'processed_data' in data['system_faults']:
            faults_data = data['system_faults']['processed_data']
            critical_count = faults_data.get('total_critical_faults', 0)
            
            if critical_count > 0:
                self.add_error(f"Warning: {critical_count} critical system faults detected")
        
        # Check cluster state
        if 'cluster_state' in data and 'processed_data' in data['cluster_state']:
            state_data = data['cluster_state']['processed_data']
            quorum_status = state_data.get('quorum_status', 'unknown')
            
            if quorum_status != 'fully-distributed':
                self.add_error(f"Warning: APIC cluster quorum status is {quorum_status}")
        
        return len(self.errors) == 0