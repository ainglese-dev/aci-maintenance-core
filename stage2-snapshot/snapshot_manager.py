"""
Snapshot management system for ACI fabric data collection
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import sys

# Add shared utilities to path
sys.path.append(str(Path(__file__).parent.parent / "shared"))
from utils import create_timestamped_filename, ensure_directory

logger = logging.getLogger(__name__)


class SnapshotManager:
    """Manages fabric snapshots with timestamped storage and comparison"""
    
    def __init__(self, snapshots_dir: str = "snapshots", comparisons_dir: str = "comparisons"):
        self.snapshots_dir = Path(snapshots_dir)
        self.comparisons_dir = Path(comparisons_dir)
        
        # Ensure directories exist
        ensure_directory(self.snapshots_dir)
        ensure_directory(self.comparisons_dir)
        
    def create_snapshot(self, snapshot_name: str = None) -> str:
        """Create a new snapshot directory with timestamp"""
        if not snapshot_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_name = f"snapshot_{timestamp}"
        
        snapshot_path = self.snapshots_dir / snapshot_name
        ensure_directory(snapshot_path)
        
        logger.info(f"Created snapshot directory: {snapshot_path}")
        return str(snapshot_path)
    
    def save_collection_data(self, snapshot_path: str, collection_type: str, data: Dict[str, Any]):
        """Save collection data to snapshot directory"""
        snapshot_dir = Path(snapshot_path)
        
        # Save raw data as JSON
        data_file = snapshot_dir / f"{collection_type}_data.json"
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        # Save summary as text
        summary_file = snapshot_dir / f"{collection_type}_summary.txt"
        with open(summary_file, 'w') as f:
            self.write_collection_summary(f, collection_type, data)
        
        logger.info(f"Saved {collection_type} data to {snapshot_path}")
    
    def write_collection_summary(self, file_handle, collection_type: str, data: Dict[str, Any]):
        """Write human-readable summary of collection data"""
        file_handle.write(f"{collection_type.upper()} COLLECTION SUMMARY\n")
        file_handle.write("=" * 50 + "\n")
        file_handle.write(f"Collection Time: {data.get('start_time', 'Unknown')}\n")
        file_handle.write(f"Duration: {data.get('duration_seconds', 0):.2f} seconds\n")
        file_handle.write(f"Errors: {len(data.get('errors', []))}\n")
        
        if data.get('errors'):
            file_handle.write("\nErrors:\n")
            for error in data['errors']:
                file_handle.write(f"  - {error}\n")
        
        file_handle.write("\nData Summary:\n")
        
        if collection_type == 'fabric':
            self.write_fabric_summary(file_handle, data.get('data', {}))
        elif collection_type in ['leaf', 'spine']:
            self.write_device_summary(file_handle, data.get('data', {}))
        elif collection_type == 'apic':
            self.write_apic_summary(file_handle, data.get('data', {}))
    
    def write_fabric_summary(self, file_handle, data: Dict[str, Any]):
        """Write fabric-wide data summary"""
        for data_type, info in data.items():
            if isinstance(info, dict) and 'count' in info:
                file_handle.write(f"  {data_type}: {info['count']} records\n")
                if 'description' in info:
                    file_handle.write(f"    Description: {info['description']}\n")
    
    def write_device_summary(self, file_handle, data: Dict[str, Any]):
        """Write device-specific data summary"""
        if 'device_info' in data:
            device_info = data['device_info']
            file_handle.write(f"  Device: {device_info.get('name', 'Unknown')}\n")
            file_handle.write(f"  Type: {device_info.get('device_type', 'Unknown')}\n")
            file_handle.write(f"  Node ID: {device_info.get('node_id', 'Unknown')}\n")
        
        file_handle.write("\nCollected Data:\n")
        for data_type, info in data.items():
            if data_type != 'device_info' and isinstance(info, dict):
                if 'processed_data' in info:
                    processed = info['processed_data']
                    file_handle.write(f"  {data_type}:\n")
                    
                    # Write key metrics
                    for key, value in processed.items():
                        if isinstance(value, (int, float, str)) and not key.endswith('_list'):
                            file_handle.write(f"    {key}: {value}\n")
    
    def write_apic_summary(self, file_handle, data: Dict[str, Any]):
        """Write APIC-specific data summary"""
        for data_type, info in data.items():
            if isinstance(info, dict) and 'processed_data' in info:
                processed = info['processed_data']
                file_handle.write(f"  {data_type}:\n")
                
                for key, value in processed.items():
                    if isinstance(value, (int, float, str)) and not key.endswith('_list'):
                        file_handle.write(f"    {key}: {value}\n")
    
    def create_overall_summary(self, snapshot_path: str, collections: Dict[str, Any]):
        """Create overall snapshot summary"""
        snapshot_dir = Path(snapshot_path)
        summary_file = snapshot_dir / "snapshot_summary.txt"
        
        with open(summary_file, 'w') as f:
            f.write("ACI FABRIC SNAPSHOT SUMMARY\n")
            f.write("=" * 50 + "\n")
            f.write(f"Snapshot Directory: {snapshot_dir.name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Collection overview
            f.write("COLLECTIONS COMPLETED:\n")
            total_errors = 0
            
            for collection_type, data in collections.items():
                if data:
                    error_count = len(data.get('errors', []))
                    total_errors += error_count
                    status = "✓" if error_count == 0 else f"⚠ ({error_count} errors)"
                    f.write(f"  {collection_type}: {status}\n")
                else:
                    f.write(f"  {collection_type}: ✗ Failed\n")
                    total_errors += 1
            
            f.write(f"\nTotal Errors: {total_errors}\n")
            
            # Health assessment
            if total_errors == 0:
                f.write("\n🟢 FABRIC STATUS: HEALTHY\n")
                f.write("All collections completed successfully\n")
            elif total_errors <= 3:
                f.write("\n🟡 FABRIC STATUS: WARNING\n")
                f.write("Some minor issues detected\n")
            else:
                f.write("\n🔴 FABRIC STATUS: CRITICAL\n")
                f.write("Multiple issues detected - investigation required\n")
            
            # Recommendations
            f.write("\nRECOMMENDATIONS:\n")
            if total_errors == 0:
                f.write("  - Fabric appears healthy for maintenance window\n")
                f.write("  - Proceed with planned activities\n")
            else:
                f.write("  - Review error details in individual collection files\n")
                f.write("  - Address critical issues before maintenance\n")
                f.write("  - Consider delaying maintenance if major issues exist\n")
        
        logger.info(f"Created overall summary: {summary_file}")
    
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all available snapshots with metadata"""
        snapshots = []
        
        for snapshot_dir in self.snapshots_dir.iterdir():
            if snapshot_dir.is_dir():
                snapshot_info = {
                    'name': snapshot_dir.name,
                    'path': str(snapshot_dir),
                    'created': datetime.fromtimestamp(snapshot_dir.stat().st_mtime),
                    'files': list(snapshot_dir.glob('*_data.json'))
                }
                snapshots.append(snapshot_info)
        
        # Sort by creation time (newest first)
        snapshots.sort(key=lambda x: x['created'], reverse=True)
        return snapshots
    
    def load_snapshot_data(self, snapshot_path: str) -> Dict[str, Any]:
        """Load all data from a snapshot"""
        snapshot_dir = Path(snapshot_path)
        snapshot_data = {}
        
        # Load all JSON data files
        for data_file in snapshot_dir.glob('*_data.json'):
            collection_type = data_file.stem.replace('_data', '')
            
            try:
                with open(data_file, 'r') as f:
                    snapshot_data[collection_type] = json.load(f)
                logger.debug(f"Loaded {collection_type} data from {data_file}")
            except Exception as e:
                logger.error(f"Failed to load {data_file}: {e}")
                snapshot_data[collection_type] = None
        
        return snapshot_data
    
    def find_baseline_snapshot(self) -> Optional[str]:
        """Find the most recent snapshot to use as baseline"""
        snapshots = self.list_snapshots()
        
        if snapshots:
            baseline = snapshots[0]  # Most recent
            logger.info(f"Found baseline snapshot: {baseline['name']}")
            return baseline['path']
        else:
            logger.warning("No baseline snapshot found")
            return None
    
    def create_comparison_report(self, baseline_path: str, current_path: str) -> str:
        """Create comparison report between two snapshots"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = f"comparison_report_{timestamp}"
        report_path = self.comparisons_dir / f"{report_name}.txt"
        
        baseline_data = self.load_snapshot_data(baseline_path)
        current_data = self.load_snapshot_data(current_path)
        
        with open(report_path, 'w') as f:
            f.write("ACI FABRIC COMPARISON REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Baseline: {Path(baseline_path).name}\n")
            f.write(f"Current:  {Path(current_path).name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Compare each collection type
            all_collections = set(baseline_data.keys()) | set(current_data.keys())
            
            for collection_type in sorted(all_collections):
                f.write(f"{collection_type.upper()} COMPARISON:\n")
                f.write("-" * 30 + "\n")
                
                baseline_collection = baseline_data.get(collection_type)
                current_collection = current_data.get(collection_type)
                
                if not baseline_collection and not current_collection:
                    f.write("  No data in either snapshot\n\n")
                elif not baseline_collection:
                    f.write("  ✓ New collection added\n\n")
                elif not current_collection:
                    f.write("  ✗ Collection missing in current snapshot\n\n")
                else:
                    # Compare the collections
                    changes = self.compare_collections(baseline_collection, current_collection)
                    if changes:
                        for change in changes:
                            f.write(f"  {change}\n")
                    else:
                        f.write("  ✓ No significant changes detected\n")
                    f.write("\n")
        
        logger.info(f"Created comparison report: {report_path}")
        return str(report_path)
    
    def compare_collections(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> List[str]:
        """Compare two collection datasets and return list of changes"""
        changes = []
        
        # Compare error counts
        baseline_errors = len(baseline.get('errors', []))
        current_errors = len(current.get('errors', []))
        
        if current_errors > baseline_errors:
            changes.append(f"⚠ Errors increased: {baseline_errors} → {current_errors}")
        elif current_errors < baseline_errors:
            changes.append(f"✓ Errors decreased: {baseline_errors} → {current_errors}")
        
        # Compare data content (basic comparison)
        baseline_data = baseline.get('data', {})
        current_data = current.get('data', {})
        
        for key in baseline_data.keys():
            if key not in current_data:
                changes.append(f"⚠ Missing data: {key}")
            else:
                # Compare counts if available
                baseline_count = self.extract_count(baseline_data[key])
                current_count = self.extract_count(current_data[key])
                
                if baseline_count is not None and current_count is not None:
                    if abs(current_count - baseline_count) > 0:
                        changes.append(f"△ {key} count: {baseline_count} → {current_count}")
        
        # Check for new data
        for key in current_data.keys():
            if key not in baseline_data:
                changes.append(f"✓ New data: {key}")
        
        return changes
    
    def extract_count(self, data: Any) -> Optional[int]:
        """Extract count value from various data structures"""
        if isinstance(data, dict):
            if 'count' in data:
                return data['count']
            elif 'processed_data' in data:
                processed = data['processed_data']
                if isinstance(processed, dict):
                    # Look for total counts
                    for key, value in processed.items():
                        if 'total' in key.lower() and isinstance(value, int):
                            return value
        
        return None