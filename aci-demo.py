#!/usr/bin/env python3
"""
ACI Inventory Demo Tool
Simple one-file script to convert APIC JSON exports to Ansible inventory

Usage: python aci-demo.py
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Rich imports with graceful fallback
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.text import Text
    from rich.prompt import Prompt
    from rich import box
    from rich.columns import Columns
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Initialize console
if RICH_AVAILABLE:
    console = Console()
else:
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


def rich_input(prompt_text, default=None):
    """Rich input with fallback"""
    if RICH_AVAILABLE and console:
        if default:
            return Prompt.ask(prompt_text, default=default)
        else:
            return Prompt.ask(prompt_text)
    else:
        if default:
            response = input(f"{prompt_text} [{default}]: ").strip()
            return response if response else default
        else:
            return input(f"{prompt_text}: ").strip()


def show_header():
    """Display application header with Rich styling"""
    if RICH_AVAILABLE and console:
        # Create title with gradient effect
        title = Text("ACI Inventory Demo Tool", style="bold blue")
        subtitle = Text("Convert APIC JSON exports to Ansible inventory", style="dim")
        
        header_content = Align.center(Text.assemble(title, "\n", subtitle))
        
        panel = Panel(
            header_content,
            box=box.DOUBLE,
            style="blue",
            padding=(1, 2)
        )
        console.print()
        console.print(panel)
        console.print()
    else:
        print("ACI Inventory Demo Tool")
        print("=" * 40)


def find_json_files():
    """Auto-detect JSON files in current directory"""
    json_files = []
    for file in os.listdir('.'):
        if file.endswith('.json'):
            json_files.append(file)
    return json_files


def load_json_file(filepath):
    """Load and parse JSON file with Rich status"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        rich_print(f"✓ Loaded {filepath}", "green", "✓ ")
        return data
    except Exception as e:
        rich_print(f"✗ Error loading {filepath}: {e}", "red", "✗ ")
        return None


def extract_fabric_nodes(fabric_data):
    """Extract nodes from fabric inventory JSON"""
    nodes = []
    
    if not fabric_data or 'imdata' not in fabric_data:
        rich_print("✗ Invalid fabric inventory format", "red", "✗ ")
        return nodes
    
    for item in fabric_data['imdata']:
        if 'fabricNode' in item:
            attrs = item['fabricNode']['attributes']
            node = {
                'id': attrs.get('id', ''),
                'name': attrs.get('name', ''),
                'role': attrs.get('role', ''),
                'model': attrs.get('model', ''),
                'serial': attrs.get('serial', ''),
                'podId': attrs.get('podId', '1'),
                'ip': None
            }
            nodes.append(node)
    
    rich_print(f"✓ Found {len(nodes)} fabric nodes", "green", "✓ ")
    return nodes


def extract_management_ips(mgmt_data):
    """Extract management IPs from static node management JSON with type detection"""
    inband_ips = {}
    outband_ips = {}
    
    if not mgmt_data or 'imdata' not in mgmt_data:
        rich_print("✗ Invalid management IP format", "red", "✗ ")
        return {}, {}, None
    
    for item in mgmt_data['imdata']:
        # Handle in-band management
        if 'mgmtRsInBStNode' in item:
            attrs = item['mgmtRsInBStNode']['attributes']
            dn = attrs.get('tDn', attrs.get('dn', ''))
            if '/node-' in dn:
                node_id = dn.split('/node-')[1].split('/')[0]
                ip = attrs.get('addr', '')
                if ip:
                    inband_ips[node_id] = ip
        
        # Handle out-of-band management
        elif 'mgmtRsOoBStNode' in item:
            attrs = item['mgmtRsOoBStNode']['attributes']
            dn = attrs.get('tDn', attrs.get('dn', ''))
            if '/node-' in dn:
                node_id = dn.split('/node-')[1].split('/')[0]
                ip = attrs.get('addr', '')
                if ip:
                    outband_ips[node_id] = ip
    
    # Display findings with color coding
    rich_print(f"✓ Found {len(inband_ips)} in-band management IPs", "cyan", "✓ ")
    rich_print(f"✓ Found {len(outband_ips)} out-of-band management IPs", "blue", "✓ ")
    
    # Determine preference
    mgmt_preference = None
    if inband_ips and outband_ips:
        rich_print("\nBoth in-band and out-of-band management IPs found.", "yellow")
        choice = rich_input("Prefer (i)n-band or (o)ut-of-band?", "out-of-band").lower()
        if choice.startswith('i'):
            mgmt_preference = 'inband'
            rich_print("Using in-band management IPs", "cyan", "→ ")
        else:
            mgmt_preference = 'outband'
            rich_print("Using out-of-band management IPs", "blue", "→ ")
    elif inband_ips:
        mgmt_preference = 'inband'
        rich_print("Using in-band management IPs", "cyan", "→ ")
    elif outband_ips:
        mgmt_preference = 'outband'
        rich_print("Using out-of-band management IPs", "blue", "→ ")
    else:
        rich_print("✗ No management IPs found", "red", "✗ ")
        return {}, {}, None
    
    return inband_ips, outband_ips, mgmt_preference


def merge_node_data(nodes, inband_ips, outband_ips, mgmt_preference):
    """Merge fabric nodes with management IPs based on preference"""
    if mgmt_preference == 'inband':
        preferred_ips = inband_ips
        fallback_ips = outband_ips
    else:
        preferred_ips = outband_ips
        fallback_ips = inband_ips
    
    for node in nodes:
        node_id = node['id']
        if node_id in preferred_ips:
            node['ip'] = preferred_ips[node_id]
            node['mgmt_type'] = mgmt_preference
        elif node_id in fallback_ips:
            node['ip'] = fallback_ips[node_id]
            node['mgmt_type'] = 'inband' if mgmt_preference == 'outband' else 'outband'
        else:
            node['ip'] = None
            node['mgmt_type'] = None
    
    # Count nodes with IPs
    with_ips = len([n for n in nodes if n['ip']])
    mgmt_type_name = 'in-band' if mgmt_preference == 'inband' else 'out-of-band'
    mgmt_color = 'cyan' if mgmt_preference == 'inband' else 'blue'
    rich_print(f"✓ Matched {with_ips} nodes with {mgmt_type_name} management IPs", mgmt_color, "✓ ")
    return nodes


def generate_ansible_inventory(nodes, mgmt_preference):
    """Generate Ansible inventory from node data with management type info"""
    inventory = []
    inventory.append("# ACI Inventory Generated by aci-demo.py")
    inventory.append(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Add management type information
    mgmt_type_name = 'In-band' if mgmt_preference == 'inband' else 'Out-of-band'
    inventory.append(f"# Management Network: {mgmt_type_name}")
    
    # Count mixed management types
    mixed_count = len([n for n in nodes if n.get('mgmt_type') and n['mgmt_type'] != mgmt_preference])
    if mixed_count > 0:
        inventory.append(f"# Note: {mixed_count} nodes using fallback management type")
    
    inventory.append("")
    
    # Group nodes by type and pod
    pods = {}
    for node in nodes:
        pod = node['podId']
        if pod not in pods:
            pods[pod] = {'apics': [], 'spines': [], 'leaves': []}
        
        role = node['role'].lower()
        if role == 'controller':
            pods[pod]['apics'].append(node)
        elif role == 'spine':
            pods[pod]['spines'].append(node)
        elif role == 'leaf':
            pods[pod]['leaves'].append(node)
    
    # Generate inventory sections
    for pod_id, pod_nodes in pods.items():
        # APICs
        if pod_nodes['apics']:
            inventory.append(f"[apics_pod_{pod_id}]")
            for i, node in enumerate(pod_nodes['apics'], 1):
                ip = node['ip'] if node['ip'] else 'NO_IP'
                inventory.append(f"{node['name']} ansible_host={ip} priority={i}")
            inventory.append("")
        
        # Spines
        if pod_nodes['spines']:
            inventory.append(f"[spines_pod_{pod_id}]")
            for node in pod_nodes['spines']:
                ip = node['ip'] if node['ip'] else 'NO_IP'
                inventory.append(f"{node['name']} ansible_host={ip} node_id={node['id']}")
            inventory.append("")
        
        # Leaves  
        if pod_nodes['leaves']:
            inventory.append(f"[leaves_pod_{pod_id}]")
            for node in pod_nodes['leaves']:
                ip = node['ip'] if node['ip'] else 'NO_IP'
                inventory.append(f"{node['name']} ansible_host={ip} node_id={node['id']}")
            inventory.append("")
    
    # Group children
    inventory.append("[apics:children]")
    for pod_id in pods.keys():
        if pods[pod_id]['apics']:
            inventory.append(f"apics_pod_{pod_id}")
    inventory.append("")
    
    inventory.append("[spines:children]")
    for pod_id in pods.keys():
        if pods[pod_id]['spines']:
            inventory.append(f"spines_pod_{pod_id}")
    inventory.append("")
    
    inventory.append("[leaves:children]")
    for pod_id in pods.keys():
        if pods[pod_id]['leaves']:
            inventory.append(f"leaves_pod_{pod_id}")
    inventory.append("")
    
    # Global variables
    inventory.append("[all:vars]")
    inventory.append("ansible_user=admin")
    inventory.append("ansible_password=CHANGE_ME")
    inventory.append("ansible_connection=httpapi")
    inventory.append("ansible_httpapi_use_ssl=true")
    inventory.append("ansible_httpapi_validate_certs=false")
    inventory.append("ansible_network_os=aci")
    
    return '\n'.join(inventory)


def print_summary(nodes, mgmt_preference):
    """Print generation summary with Rich styling"""
    if not RICH_AVAILABLE or not console:
        # Fallback to plain text
        total = len(nodes)
        apics = len([n for n in nodes if n['role'] == 'controller'])
        spines = len([n for n in nodes if n['role'] == 'spine'])
        leaves = len([n for n in nodes if n['role'] == 'leaf'])
        with_ips = len([n for n in nodes if n['ip']])
        inband_count = len([n for n in nodes if n.get('mgmt_type') == 'inband'])
        outband_count = len([n for n in nodes if n.get('mgmt_type') == 'outband'])
        mgmt_type_name = 'In-band' if mgmt_preference == 'inband' else 'Out-of-band'
        
        print(f"\n{'='*40}")
        print("INVENTORY GENERATION SUMMARY")
        print(f"{'='*40}")
        print(f"Total nodes: {total}")
        print(f"APICs: {apics}")
        print(f"Spines: {spines}")
        print(f"Leaves: {leaves}")
        print(f"Nodes with IPs: {with_ips}")
        print(f"Management type: {mgmt_type_name}")
        if inband_count > 0:
            print(f"  In-band IPs: {inband_count}")
        if outband_count > 0:
            print(f"  Out-of-band IPs: {outband_count}")
        print(f"{'='*40}")
        return
    
    # Rich implementation
    total = len(nodes)
    apics = len([n for n in nodes if n['role'] == 'controller'])
    spines = len([n for n in nodes if n['role'] == 'spine'])
    leaves = len([n for n in nodes if n['role'] == 'leaf'])
    with_ips = len([n for n in nodes if n['ip']])
    
    # Count by management type
    inband_count = len([n for n in nodes if n.get('mgmt_type') == 'inband'])
    outband_count = len([n for n in nodes if n.get('mgmt_type') == 'outband'])
    
    # Create main summary table
    summary_table = Table(title="Inventory Generation Summary", box=box.ROUNDED, 
                         title_style="bold green")
    summary_table.add_column("Component", style="cyan", no_wrap=True)
    summary_table.add_column("Count", style="magenta", justify="right")
    
    summary_table.add_row("Total Nodes", str(total))
    summary_table.add_row("APICs", str(apics))
    summary_table.add_row("Spine Switches", str(spines))
    summary_table.add_row("Leaf Switches", str(leaves))
    summary_table.add_row("Nodes with IPs", str(with_ips))
    
    # Create management type table
    mgmt_table = Table(title="Management Network Summary", box=box.ROUNDED,
                      title_style="bold blue")
    mgmt_table.add_column("Network Type", style="cyan")
    mgmt_table.add_column("Node Count", style="magenta", justify="right")
    mgmt_table.add_column("Status", style="green")
    
    mgmt_type_name = 'In-band' if mgmt_preference == 'inband' else 'Out-of-band'
    primary_style = "cyan bold" if mgmt_preference == 'inband' else "blue bold"
    
    if inband_count > 0:
        status = "✓ Primary" if mgmt_preference == 'inband' else "Fallback"
        mgmt_table.add_row("In-band", str(inband_count), status)
    
    if outband_count > 0:
        status = "✓ Primary" if mgmt_preference == 'outband' else "Fallback"
        mgmt_table.add_row("Out-of-band", str(outband_count), status)
    
    # Display tables
    console.print()
    console.print(summary_table)
    console.print()
    console.print(mgmt_table)
    console.print()


def show_file_selection_table(json_files):
    """Display file selection as Rich table"""
    if RICH_AVAILABLE and console:
        table = Table(title="Available JSON Files", box=box.ROUNDED)
        table.add_column("No.", style="cyan", width=4)
        table.add_column("Filename", style="magenta")
        table.add_column("Size", style="green", justify="right")
        
        for i, file in enumerate(json_files, 1):
            try:
                size = os.path.getsize(file)
                size_str = f"{size:,} bytes"
            except:
                size_str = "Unknown"
            table.add_row(str(i), file, size_str)
        
        console.print()
        console.print(table)
        console.print()
    else:
        # Fallback
        print("\nSelect fabric inventory file:")
        for i, file in enumerate(json_files, 1):
            print(f"{i}. {file}")


def main():
    """Main demo function with Rich enhancements"""
    # Show header
    show_header()
    
    # Auto-detect JSON files
    json_files = find_json_files()
    if not json_files:
        if RICH_AVAILABLE and console:
            error_panel = Panel(
                "[red]✗ No JSON files found in current directory[/red]\n\n"
                "[yellow]To use this tool:[/yellow]\n"
                "1. Export 'Fabric Inventory' from APIC GUI as JSON\n"
                "2. Export 'Static Node Management' from APIC GUI as JSON\n"
                "3. Place both files in this directory\n"
                "4. Run: python aci-demo.py",
                title="Setup Required",
                box=box.ROUNDED,
                style="red"
            )
            console.print(error_panel)
        else:
            print("✗ No JSON files found in current directory")
            print("\nTo use this tool:")
            print("1. Export 'Fabric Inventory' from APIC GUI as JSON")
            print("2. Export 'Static Node Management' from APIC GUI as JSON")
            print("3. Place both files in this directory")
            print("4. Run: python aci-demo.py")
        return
    
    rich_print(f"Found {len(json_files)} JSON files", "green", "✓ ")
    
    # Interactive file selection
    fabric_file = None
    mgmt_file = None
    
    show_file_selection_table(json_files)
    
    try:
        choice = rich_input("Enter number", "auto-detect").strip()
        if choice != "auto-detect":
            fabric_file = json_files[int(choice) - 1]
        else:
            # Auto-detect
            for file in json_files:
                if 'fabric' in file.lower() or 'inventory' in file.lower():
                    fabric_file = file
                    break
            if not fabric_file:
                fabric_file = json_files[0]
    except:
        fabric_file = json_files[0]
    
    rich_print(f"→ Using fabric file: {fabric_file}", "cyan", "→ ")
    
    # Select management IP file
    remaining_files = [f for f in json_files if f != fabric_file]
    if remaining_files:
        rich_print(f"→ Using management IP file: {remaining_files[0]}", "blue", "→ ")
        mgmt_file = remaining_files[0]
    
    # Process files
    rich_print("\nProcessing files...", "yellow", "⚙ ")
    
    # Load fabric inventory
    fabric_data = load_json_file(fabric_file)
    if not fabric_data:
        return
    
    nodes = extract_fabric_nodes(fabric_data)
    if not nodes:
        return
    
    # Load management IPs if available
    mgmt_preference = None
    if mgmt_file:
        mgmt_data = load_json_file(mgmt_file)
        if mgmt_data:
            inband_ips, outband_ips, mgmt_preference = extract_management_ips(mgmt_data)
            if mgmt_preference:
                nodes = merge_node_data(nodes, inband_ips, outband_ips, mgmt_preference)
    
    # Generate inventory
    rich_print("\nGenerating Ansible inventory...", "yellow", "⚙ ")
    inventory_content = generate_ansible_inventory(nodes, mgmt_preference)
    
    # Write inventory file
    inventory_file = "aci-inventory.ini"
    with open(inventory_file, 'w') as f:
        f.write(inventory_content)
    
    rich_print(f"✓ Inventory saved to: {inventory_file}", "green", "✓ ")
    
    # Show summary
    print_summary(nodes, mgmt_preference)
    
    # Final completion message
    if RICH_AVAILABLE and console:
        completion_panel = Panel(
            f"[green]✓ Demo completed successfully![/green]\n\n"
            f"[cyan]Use the generated inventory with:[/cyan]\n"
            f"[white]ansible-playbook -i {inventory_file} your-playbook.yml[/white]\n\n"
            f"[dim]The inventory includes management IPs, node IDs, and priority settings[/dim]",
            title="🎉 Success",
            box=box.ROUNDED,
            style="green"
        )
        console.print(completion_panel)
    else:
        print(f"\nDemo completed! Use the inventory with:")
        print(f"ansible-playbook -i {inventory_file} your-playbook.yml")


if __name__ == '__main__':
    main()