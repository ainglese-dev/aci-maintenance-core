"""
Device information data structures for ACI maintenance operations
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class DeviceInfo:
    """Information about a network device in the ACI fabric"""
    name: str
    hostname: str
    username: str = ""
    password: str = ""
    device_type: str = "unknown"  # apic, leaf, spine, other
    node_id: Optional[int] = None
    priority: int = 1
    port: int = 22
    
    def __post_init__(self):
        """Validate device information after initialization"""
        if not self.name:
            raise ValueError("Device name cannot be empty")
        if not self.hostname:
            raise ValueError("Device hostname cannot be empty")
        
        # Set default ports based on device type
        if self.device_type == 'apic' and self.port == 22:
            self.port = 443
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert device info to dictionary"""
        return {
            'name': self.name,
            'hostname': self.hostname,
            'username': self.username,
            'password': self.password,
            'device_type': self.device_type,
            'node_id': self.node_id,
            'priority': self.priority,
            'port': self.port
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceInfo':
        """Create device info from dictionary"""
        return cls(
            name=data.get('name', ''),
            hostname=data.get('hostname', ''),
            username=data.get('username', ''),
            password=data.get('password', ''),
            device_type=data.get('device_type', 'unknown'),
            node_id=data.get('node_id'),
            priority=data.get('priority', 1),
            port=data.get('port', 22)
        )
    
    def is_apic(self) -> bool:
        """Check if this is an APIC controller"""
        return self.device_type == 'apic'
    
    def is_switch(self) -> bool:
        """Check if this is a switch (leaf or spine)"""
        return self.device_type in ['leaf', 'spine']
    
    def __str__(self) -> str:
        """String representation of device"""
        return f"{self.device_type.upper()}: {self.name} ({self.hostname})"