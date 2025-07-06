#!/usr/bin/env python3
"""
JSON Validation Script for ACI Maintenance Core
Validates JSON files collected from APIC for proper structure and content
"""

import json
import os
import sys
from pathlib import Path

# Rich imports with graceful fallback
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


def rich_print(text, style=None, fallback_prefix=""):
    """Print with Rich styling or fallback to plain text"""
    if RICH_AVAILABLE and console:
        if style:
            console.print(text, style=style)
        else:
            console.print(text)
    else:
        print(f"{fallback_prefix}{text}")


def show_header():
    """Display validation header"""
    if RICH_AVAILABLE and console:
        header = Panel(
            "[bold blue]ACI JSON Validation Tool[/bold blue]\n"
            "[dim]Validates APIC JSON exports for ACI Maintenance Core[/dim]",
            style="blue"
        )
        console.print(header)
    else:
        print("ACI JSON Validation Tool")
        print("=" * 40)


def validate_json_structure(filepath, data):
    """Validate basic JSON structure"""
    errors = []
    warnings = []
    
    # Check for imdata array
    if "imdata" not in data:
        errors.append("Missing required 'imdata' root array")
        return errors, warnings
    
    if not isinstance(data["imdata"], list):
        errors.append("'imdata' must be an array")
        return errors, warnings
    
    if len(data["imdata"]) == 0:
        warnings.append("'imdata' array is empty")
    
    # Check for totalCount (optional but expected)
    if "totalCount" not in data:
        warnings.append("Missing 'totalCount' field (optional)")
    
    return errors, warnings


def validate_fabric_inventory(data):
    """Validate fabric inventory JSON structure"""
    errors = []
    warnings = []
    stats = {"controllers": 0, "spines": 0, "leaves": 0, "other": 0}
    
    if "imdata" not in data:
        return ["Missing 'imdata' array"], [], stats
    
    for item in data["imdata"]:
        if "fabricNode" in item:
            node = item["fabricNode"]
            if "attributes" not in node:
                errors.append("fabricNode missing 'attributes'")
                continue
            
            attrs = node["attributes"]
            
            # Check required fields
            required_fields = ["id", "name", "role"]
            for field in required_fields:
                if field not in attrs:
                    errors.append(f"fabricNode missing required field: {field}")
            
            # Count node types
            role = attrs.get("role", "").lower()
            if role == "controller":
                stats["controllers"] += 1
            elif role == "spine":
                stats["spines"] += 1
            elif role == "leaf":
                stats["leaves"] += 1
            else:
                stats["other"] += 1
            
            # Check optional but important fields
            optional_fields = ["model", "serial", "podId", "fabricSt"]
            for field in optional_fields:
                if field not in attrs:
                    warnings.append(f"fabricNode {attrs.get('name', 'unknown')} missing {field}")
    
    # Validate fabric composition
    if stats["controllers"] == 0:
        errors.append("No APIC controllers found in fabric")
    elif stats["controllers"] < 3:
        warnings.append(f"Only {stats['controllers']} APIC controllers found (typical: 3)")
    
    if stats["spines"] == 0 and stats["leaves"] == 0:
        errors.append("No spine or leaf switches found")
    
    return errors, warnings, stats


def validate_management_ips(data):
    """Validate management IP JSON structure"""
    errors = []
    warnings = []
    stats = {"inband": 0, "outband": 0, "nodes_with_ips": set()}
    
    if "imdata" not in data:
        return ["Missing 'imdata' array"], [], stats
    
    for item in data["imdata"]:
        mgmt_type = None
        if "mgmtRsInBStNode" in item:
            mgmt_obj = item["mgmtRsInBStNode"]
            mgmt_type = "inband"
            stats["inband"] += 1
        elif "mgmtRsOoBStNode" in item:
            mgmt_obj = item["mgmtRsOoBStNode"]
            mgmt_type = "outband"
            stats["outband"] += 1
        else:
            warnings.append("Unknown management object type in imdata")
            continue
        
        if "attributes" not in mgmt_obj:
            errors.append(f"{mgmt_type} management object missing 'attributes'")
            continue
        
        attrs = mgmt_obj["attributes"]
        
        # Check required fields
        required_fields = ["tDn", "addr"]
        for field in required_fields:
            if field not in attrs:
                errors.append(f"{mgmt_type} management object missing required field: {field}")
        
        # Extract node ID from tDn for tracking
        tdn = attrs.get("tDn", "")
        if "node-" in tdn:
            node_id = tdn.split("node-")[-1].rstrip("]")
            stats["nodes_with_ips"].add(node_id)
        
        # Validate IP address format (basic check)
        addr = attrs.get("addr", "")
        if addr and not _is_valid_ip(addr):
            warnings.append(f"Possibly invalid IP address: {addr}")
    
    # Summary validation
    if stats["inband"] == 0 and stats["outband"] == 0:
        errors.append("No management IP assignments found")
    
    return errors, warnings, stats


def _is_valid_ip(ip_str):
    """Basic IP address validation"""
    try:
        parts = ip_str.split(".")
        if len(parts) != 4:
            return False
        for part in parts:
            if not (0 <= int(part) <= 255):
                return False
        return True
    except (ValueError, AttributeError):
        return False


def validate_file(filepath):
    """Validate a single JSON file"""
    rich_print(f"\n📄 Validating: {filepath}", "bold")
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        rich_print(f"❌ JSON parsing error: {e}", "red")
        return False
    except Exception as e:
        rich_print(f"❌ File error: {e}", "red")
        return False
    
    # Basic structure validation
    base_errors, base_warnings = validate_json_structure(filepath, data)
    
    # Specific validation based on content
    file_type = detect_file_type(data)
    specific_errors = []
    specific_warnings = []
    stats = {}
    
    if file_type == "fabric_inventory":
        specific_errors, specific_warnings, stats = validate_fabric_inventory(data)
    elif file_type == "management_ips":
        specific_errors, specific_warnings, stats = validate_management_ips(data)
    else:
        specific_warnings.append("Unknown file type - unable to perform specific validation")
    
    # Combine results
    all_errors = base_errors + specific_errors
    all_warnings = base_warnings + specific_warnings
    
    # Display results
    if all_errors:
        rich_print(f"❌ {len(all_errors)} errors found:", "red")
        for error in all_errors:
            rich_print(f"   • {error}", "red")
    
    if all_warnings:
        rich_print(f"⚠️  {len(all_warnings)} warnings:", "yellow")
        for warning in all_warnings:
            rich_print(f"   • {warning}", "yellow")
    
    if not all_errors and not all_warnings:
        rich_print("✅ File validation passed", "green")
    elif not all_errors:
        rich_print("✅ File structure valid (warnings present)", "green")
    
    # Display statistics
    if stats and file_type == "fabric_inventory":
        rich_print(f"📊 Fabric composition: {stats['controllers']} controllers, "
                  f"{stats['spines']} spines, {stats['leaves']} leaves", "cyan")
    elif stats and file_type == "management_ips":
        rich_print(f"📊 Management IPs: {stats['inband']} in-band, "
                  f"{stats['outband']} out-of-band, "
                  f"{len(stats['nodes_with_ips'])} nodes", "cyan")
    
    return len(all_errors) == 0


def detect_file_type(data):
    """Detect the type of JSON file based on content"""
    if "imdata" not in data:
        return "unknown"
    
    for item in data["imdata"]:
        if "fabricNode" in item:
            return "fabric_inventory"
        elif "mgmtRsInBStNode" in item or "mgmtRsOoBStNode" in item:
            return "management_ips"
    
    return "unknown"


def find_json_files():
    """Find JSON files in current directory"""
    json_files = []
    for file in os.listdir('.'):
        if file.endswith('.json'):
            json_files.append(file)
    return sorted(json_files)


def main():
    """Main validation function"""
    show_header()
    
    # Find JSON files
    json_files = find_json_files()
    
    if not json_files:
        rich_print("❌ No JSON files found in current directory", "red")
        rich_print("\nPlace your APIC JSON exports in this directory and run again.", "dim")
        return 1
    
    rich_print(f"\n🔍 Found {len(json_files)} JSON files to validate", "blue")
    
    all_valid = True
    for json_file in json_files:
        if not validate_file(json_file):
            all_valid = False
    
    # Summary
    if RICH_AVAILABLE and console:
        console.print()
        if all_valid:
            console.print("🎉 All files passed validation!", style="bold green")
            console.print("You can proceed with the inventory generator.", style="dim")
        else:
            console.print("❌ Some files have validation errors", style="bold red")
            console.print("Fix the errors above before proceeding.", style="dim")
    else:
        print()
        if all_valid:
            print("✓ All files passed validation!")
        else:
            print("✗ Some files have validation errors")
    
    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())