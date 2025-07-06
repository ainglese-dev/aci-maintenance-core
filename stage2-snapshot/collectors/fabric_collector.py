"""
Fabric-wide data collector using APIC REST API
"""

import logging
from typing import Dict, List, Any, Optional
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)


class FabricCollector(BaseCollector):
    """Collects fabric-wide data via APIC REST API"""
    
    # APIC REST API endpoints for fabric-wide data
    FABRIC_ENDPOINTS = {
        'topology': {
            'endpoint': '/api/class/fabricNode.json',
            'description': 'Fabric nodes and their status'
        },
        'links': {
            'endpoint': '/api/class/fabricLink.json',
            'description': 'Fabric links between nodes'
        },
        'faults': {
            'endpoint': '/api/class/faultInst.json',
            'params': {'query-target-filter': 'eq(faultInst.severity,"major","critical")'},
            'description': 'Major and critical faults'
        },
        'health': {
            'endpoint': '/api/class/healthInst.json',
            'description': 'Health scores for fabric objects'
        },
        'discovery': {
            'endpoint': '/api/class/dhcpClient.json',
            'description': 'Fabric discovery and node registration'
        },
        'isis': {
            'endpoint': '/api/class/isisInternalRoute.json',
            'description': 'IS-IS internal routes'
        },
        'ospf': {
            'endpoint': '/api/class/ospfInternalRoute.json',
            'description': 'OSPF internal routes'
        },
        'bgp': {
            'endpoint': '/api/class/bgpInternalRoute.json',
            'description': 'BGP internal routes'
        }
    }
    
    def __init__(self):
        super().__init__("FabricCollector")
        
    def collect(self, fabric_client) -> Dict[str, Any]:
        """Collect fabric-wide data via APIC REST API"""
        self.start_collection()
        
        fabric_data = {}
        
        for data_type, config in self.FABRIC_ENDPOINTS.items():
            try:
                logger.info(f"Collecting {data_type}: {config['description']}")
                
                params = config.get('params', None)
                response = fabric_client.get_fabric_data(config['endpoint'], params)
                
                if response and 'imdata' in response:
                    fabric_data[data_type] = {
                        'endpoint': config['endpoint'],
                        'description': config['description'],
                        'count': len(response['imdata']),
                        'data': response['imdata']
                    }
                    logger.info(f"✓ Collected {len(response['imdata'])} {data_type} records")
                else:
                    self.add_error(f"No data returned for {data_type}")
                    fabric_data[data_type] = {
                        'endpoint': config['endpoint'],
                        'description': config['description'],
                        'count': 0,
                        'data': []
                    }
                    
            except Exception as e:
                self.add_error(f"Failed to collect {data_type}: {str(e)}")
                fabric_data[data_type] = {
                    'endpoint': config['endpoint'],
                    'description': config['description'],
                    'count': 0,
                    'data': [],
                    'error': str(e)
                }
        
        # Validate collected data
        self.validate_fabric_data(fabric_data)
        
        return self.end_collection(fabric_data)
    
    def validate_fabric_data(self, data: Dict[str, Any]):
        """Validate fabric data completeness"""
        critical_collections = ['topology', 'links', 'faults']
        
        for collection in critical_collections:
            if collection not in data or data[collection]['count'] == 0:
                if collection == 'topology':
                    self.add_error(f"Critical: No {collection} data - fabric discovery may be incomplete")
                elif collection == 'faults' and data[collection]['count'] == 0:
                    logger.info(f"✓ No major/critical faults found (expected for healthy fabric)")
        
        # Check for reasonable fabric size
        if 'topology' in data:
            node_count = data['topology']['count']
            if node_count < 3:
                self.add_error(f"Warning: Only {node_count} nodes found - fabric may be incomplete")
            elif node_count > 200:
                logger.warning(f"Large fabric detected: {node_count} nodes")
        
        return len(self.errors) == 0