"""
Shared Rich TUI components for ACI Maintenance stages
"""

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


def show_stage_header(stage_name, description):
    """Display stage header with Rich styling"""
    if RICH_AVAILABLE and console:
        # Create title with gradient effect
        title = Text(f"ACI Maintenance - {stage_name}", style="bold blue")
        subtitle = Text(description, style="dim")
        
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
        print(f"ACI Maintenance - {stage_name}")
        print("=" * 40)
        print(description)


def show_success_panel(title, message, next_steps=None):
    """Display success completion panel"""
    if RICH_AVAILABLE and console:
        content = f"[green]✓ {message}[/green]"
        if next_steps:
            content += f"\n\n[cyan]Next Steps:[/cyan]\n{next_steps}"
        
        panel = Panel(
            content,
            title=f"🎉 {title}",
            box=box.ROUNDED,
            style="green"
        )
        console.print(panel)
    else:
        print(f"\n✓ {message}")
        if next_steps:
            print(f"\nNext Steps:\n{next_steps}")


def create_file_table(files, title="Available Files"):
    """Create Rich table for file listings"""
    if RICH_AVAILABLE and console:
        table = Table(title=title, box=box.ROUNDED)
        table.add_column("No.", style="cyan", width=4)
        table.add_column("Filename", style="magenta")
        table.add_column("Size", style="green", justify="right")
        
        for i, file in enumerate(files, 1):
            try:
                size = file.stat().st_size if hasattr(file, 'stat') else 0
                size_str = f"{size:,} bytes"
            except:
                size_str = "Unknown"
            filename = file.name if hasattr(file, 'name') else str(file)
            table.add_row(str(i), filename, size_str)
        
        console.print()
        console.print(table)
        console.print()
        return table
    else:
        # Fallback
        print(f"\n{title}:")
        for i, file in enumerate(files, 1):
            filename = file.name if hasattr(file, 'name') else str(file)
            print(f"{i}. {filename}")
        return None