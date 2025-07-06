"""
Base collector class for fabric data collection
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Abstract base class for all data collectors"""
    
    def __init__(self, name: str):
        self.name = name
        self.collection_time = None
        self.errors = []
        
    @abstractmethod
    def collect(self, **kwargs) -> Dict[str, Any]:
        """Collect data and return structured results"""
        pass
    
    def start_collection(self):
        """Mark start of collection"""
        self.collection_time = datetime.now()
        self.errors = []
        logger.info(f"Starting {self.name} collection")
    
    def end_collection(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mark end of collection and add metadata"""
        end_time = datetime.now()
        duration = (end_time - self.collection_time).total_seconds()
        
        result = {
            'collector': self.name,
            'start_time': self.collection_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'errors': self.errors,
            'data': data
        }
        
        logger.info(f"Completed {self.name} collection in {duration:.2f}s")
        return result
    
    def add_error(self, error: str):
        """Add error message to collection results"""
        self.errors.append(error)
        logger.error(f"{self.name}: {error}")
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Basic data validation"""
        if not data:
            self.add_error("No data collected")
            return False
        return True