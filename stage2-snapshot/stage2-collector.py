#!/usr/bin/env python3
"""
Stage 2: ACI Fabric Snapshot Collector

This tool collects comprehensive fabric data before/after maintenance windows
to enable comparison and validation of fabric health.
"""

import argparse
import logging
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import json

# Add shared utilities to path
sys.path.append(str(Path(__file__).parent.parent / "shared"))
from utils import setup_logging, create_timestamped_filename

# Local imports
from inventory_parser import load_inventory_from_stage1, InventoryParser
from aci_client import FabricClient
from snapshot_manager import SnapshotManager
from collectors.fabric_collector import FabricCollector
from collectors.leaf_collector import LeafCollector
from collectors.spine_collector import SpineCollector
from collectors.apic_collector import ApicCollector


class Stage2Collector:
    """Main collector orchestrator for ACI fabric snapshots"""
    
    def __init__(self, args):
        self.args = args
        self.logger = logging.getLogger(__name__)
        self.snapshot_manager = SnapshotManager()
        self.fabric_client = None
        self.inventory = None
        
        # Initialize collectors
        self.collectors = {
            'fabric': FabricCollector(),
            'apic': ApicCollector(),
            'leaf': LeafCollector(),
            'spine': SpineCollector()
        }
    
    async def run(self):
        """Main execution flow"""
        try:
            self.logger.info("=== Stage 2: ACI Fabric Snapshot Collector ===")
            
            # Collect data based on mode
            if self.args.mode == 'collect':
                # Load inventory from Stage 1
                if not self.load_inventory():
                    return False
                
                # Get credentials
                username, password = self.get_credentials()
                
                # Initialize fabric client
                if not self.initialize_fabric_client(username, password):
                    return False
                
                # Create snapshot
                snapshot_path = self.create_snapshot()
                
                success = await self.collect_all_data(snapshot_path)
                
            elif self.args.mode == 'compare':
                success = await self.compare_snapshots()
                
            elif self.args.mode == 'list':
                success = self.list_snapshots()
                
            else:
                self.logger.error(f"Unknown mode: {self.args.mode}")
                return False
            
            if success:
                self.logger.info("✓ Stage 2 completed successfully")
                return True
            else:
                self.logger.error("✗ Stage 2 completed with errors")
                return False
                
        except KeyboardInterrupt:
            self.logger.info("Collection interrupted by user")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            return False
    
    async def load_inventory(self) -> bool:
        """Load fabric inventory from Stage 1"""
        self.logger.info("Loading fabric inventory from Stage 1...")
        
        stage1_path = getattr(self.args, 'inventory_file', None)
        self.inventory = load_inventory_from_stage1(stage1_path)
        
        if not self.inventory:
            self.logger.error("Failed to load inventory - ensure Stage 1 has been run")
            return False
        
        # Print inventory summary
        parser = InventoryParser()
        summary = parser.create_collection_summary(self.inventory)
        self.logger.info(f"Loaded inventory:\n{summary}")
        
        return True
    
    def get_credentials(self) -> tuple:
        """Get APIC credentials"""
        if self.args.username and self.args.password:
            return self.args.username, self.args.password
        
        # Interactive credential input
        import getpass
        
        print("\nAPIC Credentials Required:")
        username = input("Username: ").strip()
        password = getpass.getpass("Password: ").strip()
        
        return username, password
    
    def initialize_fabric_client(self, username: str, password: str) -> bool:
        """Initialize fabric client with APIC connection"""
        self.logger.info("Initializing fabric client...")
        
        try:
            self.fabric_client = FabricClient(
                apic_devices=self.inventory.apic_devices,
                username=username,
                password=password
            )
            
            # Test connection
            if self.fabric_client.connect():
                self.logger.info("✓ Successfully connected to fabric")
                return True
            else:
                self.logger.error("✗ Failed to connect to fabric")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize fabric client: {e}")
            return False
    
    def create_snapshot(self) -> str:
        """Create new snapshot directory"""
        snapshot_name = None
        
        if self.args.snapshot_name:
            snapshot_name = self.args.snapshot_name
        elif self.args.baseline:
            snapshot_name = f"baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        snapshot_path = self.snapshot_manager.create_snapshot(snapshot_name)
        self.logger.info(f"Created snapshot: {snapshot_path}")
        
        return snapshot_path
    
    async def collect_all_data(self, snapshot_path: str) -> bool:
        """Collect all fabric data"""
        self.logger.info("Starting fabric data collection...")
        
        collections = {}
        collection_targets = self.inventory
        
        # Collect fabric-wide data
        if not self.args.skip_fabric:
            self.logger.info("Collecting fabric-wide data...")
            fabric_data = self.collectors['fabric'].collect(self.fabric_client)
            collections['fabric'] = fabric_data
            self.snapshot_manager.save_collection_data(snapshot_path, 'fabric', fabric_data)
        
        # Collect APIC data
        if not self.args.skip_apic:
            self.logger.info("Collecting APIC controller data...")
            apic_data = self.collectors['apic'].collect(self.fabric_client)
            collections['apic'] = apic_data
            self.snapshot_manager.save_collection_data(snapshot_path, 'apic', apic_data)
        
        # Collect leaf data
        if not self.args.skip_leaf and collection_targets.leaf_devices:
            self.logger.info(f"Collecting data from {len(collection_targets.leaf_devices)} leaf switches...")
            for leaf_device in collection_targets.leaf_devices:
                try:
                    self.logger.info(f"Collecting from leaf: {leaf_device.name}")
                    leaf_data = self.collectors['leaf'].collect(self.fabric_client, leaf_device)
                    
                    collection_key = f"leaf_{leaf_device.name}"
                    collections[collection_key] = leaf_data
                    self.snapshot_manager.save_collection_data(snapshot_path, collection_key, leaf_data)
                    
                except Exception as e:
                    self.logger.error(f"Failed to collect from leaf {leaf_device.name}: {e}")
                    continue
        
        # Collect spine data
        if not self.args.skip_spine and collection_targets.spine_devices:
            self.logger.info(f"Collecting data from {len(collection_targets.spine_devices)} spine switches...")
            for spine_device in collection_targets.spine_devices:
                try:
                    self.logger.info(f"Collecting from spine: {spine_device.name}")
                    spine_data = self.collectors['spine'].collect(self.fabric_client, spine_device)
                    
                    collection_key = f"spine_{spine_device.name}"
                    collections[collection_key] = spine_data
                    self.snapshot_manager.save_collection_data(snapshot_path, collection_key, spine_data)
                    
                except Exception as e:
                    self.logger.error(f"Failed to collect from spine {spine_device.name}: {e}")
                    continue
        
        # Create overall summary
        self.snapshot_manager.create_overall_summary(snapshot_path, collections)
        
        # Check for errors
        total_errors = sum(len(data.get('errors', [])) for data in collections.values() if data)
        
        if total_errors == 0:
            self.logger.info("✓ Data collection completed successfully")
            return True
        else:
            self.logger.warning(f"⚠ Data collection completed with {total_errors} errors")
            return True  # Still consider success if we got some data
    
    async def compare_snapshots(self) -> bool:
        """Compare two snapshots"""
        if not self.args.baseline_snapshot or not self.args.current_snapshot:
            self.logger.error("Both --baseline-snapshot and --current-snapshot required for comparison")
            return False
        
        self.logger.info(f"Comparing snapshots:")
        self.logger.info(f"  Baseline: {self.args.baseline_snapshot}")
        self.logger.info(f"  Current:  {self.args.current_snapshot}")
        
        try:
            report_path = self.snapshot_manager.create_comparison_report(
                self.args.baseline_snapshot,
                self.args.current_snapshot
            )
            
            self.logger.info(f"✓ Comparison report created: {report_path}")
            
            # Optionally display report
            if self.args.show_report:
                with open(report_path, 'r') as f:
                    print("\n" + "="*80)
                    print(f.read())
                    print("="*80)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create comparison report: {e}")
            return False
    
    def list_snapshots(self) -> bool:
        """List available snapshots"""
        snapshots = self.snapshot_manager.list_snapshots()
        
        if not snapshots:
            print("No snapshots found")
            return True
        
        print(f"\nAvailable Snapshots ({len(snapshots)}):")
        print("-" * 80)
        
        for snapshot in snapshots:
            print(f"Name: {snapshot['name']}")
            print(f"Created: {snapshot['created'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Path: {snapshot['path']}")
            print(f"Files: {len(snapshot['files'])} data files")
            print("-" * 40)
        
        return True


def create_argument_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Stage 2: ACI Fabric Snapshot Collector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect baseline snapshot
  python stage2-collector.py collect --baseline
  
  # Collect current snapshot for comparison
  python stage2-collector.py collect --snapshot-name "post-maintenance"
  
  # Compare two snapshots
  python stage2-collector.py compare --baseline-snapshot baseline_20240106_143022 --current-snapshot post-maintenance
  
  # List available snapshots
  python stage2-collector.py list
        """
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='mode', help='Collection mode')
    
    # Collect subcommand
    collect_parser = subparsers.add_parser('collect', help='Collect fabric snapshot')
    collect_parser.add_argument('--inventory-file', '-i', 
                               help='Stage 1 inventory file (auto-detected if not specified)')
    collect_parser.add_argument('--snapshot-name', '-n',
                               help='Custom snapshot name')
    collect_parser.add_argument('--baseline', action='store_true',
                               help='Mark this as baseline snapshot')
    collect_parser.add_argument('--username', '-u',
                               help='APIC username')
    collect_parser.add_argument('--password', '-p',
                               help='APIC password')
    collect_parser.add_argument('--skip-fabric', action='store_true',
                               help='Skip fabric-wide collection')
    collect_parser.add_argument('--skip-apic', action='store_true',
                               help='Skip APIC-specific collection')
    collect_parser.add_argument('--skip-leaf', action='store_true',
                               help='Skip leaf switch collection')
    collect_parser.add_argument('--skip-spine', action='store_true',
                               help='Skip spine switch collection')
    
    # Compare subcommand
    compare_parser = subparsers.add_parser('compare', help='Compare two snapshots')
    compare_parser.add_argument('--baseline-snapshot', '-b', required=True,
                               help='Path to baseline snapshot')
    compare_parser.add_argument('--current-snapshot', '-c', required=True,
                               help='Path to current snapshot')
    compare_parser.add_argument('--show-report', action='store_true',
                               help='Display report after creation')
    compare_parser.add_argument('--inventory-file', '-i',
                               help='Stage 1 inventory file (auto-detected if not specified)')
    
    # List subcommand
    list_parser = subparsers.add_parser('list', help='List available snapshots')
    list_parser.add_argument('--inventory-file', '-i', 
                            help='Stage 1 inventory file (auto-detected if not specified)')
    
    # Global options
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--log-file',
                       help='Log to file instead of console')
    
    return parser


async def main():
    """Main entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    if not args.mode:
        parser.print_help()
        return 1
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level, log_file=args.log_file)
    
    # Run collector
    collector = Stage2Collector(args)
    success = await collector.run()
    
    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)