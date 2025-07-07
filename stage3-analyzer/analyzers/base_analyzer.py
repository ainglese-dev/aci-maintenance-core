"""
Base analyzer class for fabric data analysis
"""

import logging
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """Abstract base class for all data analyzers"""
    
    def __init__(self, name: str):
        self.name = name
        self.analysis_time = None
        self.errors = []
        
    @abstractmethod
    def analyze(self, **kwargs) -> Dict[str, Any]:
        """Analyze data and return structured results"""
        pass
    
    def start_analysis(self):
        """Mark start of analysis"""
        self.analysis_time = datetime.now()
        self.errors = []
        logger.info(f"Starting {self.name} analysis")
    
    def end_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mark end of analysis and add metadata"""
        end_time = datetime.now()
        duration = (end_time - self.analysis_time).total_seconds()
        
        result = {
            'analyzer': self.name,
            'start_time': self.analysis_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'errors': self.errors,
            'data': data
        }
        
        logger.info(f"Completed {self.name} analysis in {duration:.2f}s")
        
        if self.errors:
            logger.warning(f"{self.name} analysis completed with {len(self.errors)} errors")
        
        return result
    
    def add_error(self, error: str):
        """Add error to collection"""
        self.errors.append({
            'timestamp': datetime.now().isoformat(),
            'error': error
        })
        logger.error(f"{self.name}: {error}")
    
    def load_snapshot(self, snapshot_path: Path) -> Optional[Dict[str, Any]]:
        """Load and validate snapshot file"""
        try:
            if not snapshot_path.exists():
                self.add_error(f"Snapshot file not found: {snapshot_path}")
                return None
                
            with open(snapshot_path, 'r') as f:
                data = json.load(f)
                
            # Basic validation
            if 'metadata' not in data:
                self.add_error(f"Invalid snapshot format: missing metadata")
                return None
                
            logger.debug(f"Loaded snapshot: {snapshot_path}")
            return data
            
        except json.JSONDecodeError as e:
            self.add_error(f"Invalid JSON in snapshot {snapshot_path}: {e}")
            return None
        except Exception as e:
            self.add_error(f"Failed to load snapshot {snapshot_path}: {e}")
            return None
    
    def extract_devices_by_type(self, snapshot: Dict[str, Any], device_type: str) -> List[Dict[str, Any]]:
        """Extract devices of specific type from snapshot"""
        try:
            devices = []
            
            # Look for devices in the data structure
            for collector_name, collector_data in snapshot.get('data', {}).items():
                if isinstance(collector_data, dict) and 'data' in collector_data:
                    collector_devices = collector_data['data'].get(f'{device_type}_devices', [])
                    if isinstance(collector_devices, list):
                        devices.extend(collector_devices)
            
            return devices
            
        except Exception as e:
            self.add_error(f"Failed to extract {device_type} devices: {e}")
            return []
    
    def get_snapshot_metadata(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from snapshot"""
        return snapshot.get('metadata', {})
    
    def compare_values(self, before_value: Any, after_value: Any, field_name: str) -> Dict[str, Any]:
        """Compare two values and return difference information"""
        changed = before_value != after_value
        
        return {
            'field': field_name,
            'changed': changed,
            'before': before_value,
            'after': after_value,
            'change_type': self.classify_change(before_value, after_value) if changed else None
        }
    
    def classify_change(self, before_value: Any, after_value: Any) -> str:
        """Classify the type of change between two values"""
        if before_value is None and after_value is not None:
            return 'added'
        elif before_value is not None and after_value is None:
            return 'removed'
        elif isinstance(before_value, (int, float)) and isinstance(after_value, (int, float)):
            if after_value > before_value:
                return 'increased'
            else:
                return 'decreased'
        else:
            return 'modified'