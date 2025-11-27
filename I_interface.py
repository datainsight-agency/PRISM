"""
I_interface.py - User Interface Module v5.0
Handles CLI interactions with rich styling and visual enhancements

Requires: pip install rich
Fallback: Works without rich (basic styling)
"""

import json
from pathlib import Path
from datetime import datetime

# Try to import rich for enhanced styling
try:
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.prompt import Prompt, IntPrompt, Confirm
    from rich.columns import Columns
    from rich.style import Style
    from rich.box import ROUNDED, DOUBLE, HEAVY, MINIMAL
    from rich import box
    from rich.align import Align
    from rich.padding import Padding
    from rich.rule import Rule
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class Interface:
    """Manages command-line interface and user interactions with rich styling"""
    
    VERSION = "5.0"
    CODENAME = "Orchestrator"
    
    # Color scheme
    COLORS = {
        'primary': '#00D4FF',      # Cyan
        'secondary': '#BD93F9',    # Purple
        'accent': '#50FA7B',       # Green
        'warning': '#FFB86C',      # Orange
        'error': '#FF5555',        # Red
        'muted': '#6272A4',        # Gray-blue
        'success': '#50FA7B',      # Green
        'info': '#8BE9FD',         # Light cyan
    }
    
    def __init__(self, config_dir="config"):
        self.config_dir = Path(config_dir)
        self.models_config = self._load_config("models.json")
        self.settings = self._load_config("settings.json")
        
        # Initialize rich console
        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None
    
    def _load_config(self, filename):
        """Load a configuration file"""
        config_path = self.config_dir / filename
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _print(self, *args, **kwargs):
        """Print wrapper that uses rich if available"""
        if self.console:
            self.console.print(*args, **kwargs)
        else:
            # Fallback to basic print
            print(*args)
    
    def show_banner(self):
        """Display application banner with gradient styling"""
        if RICH_AVAILABLE:
            self._show_rich_banner()
        else:
            self._show_basic_banner()
    
    def _show_rich_banner(self):
        """Rich-styled banner with gradient effect"""
        
        # ASCII art with gradient coloring
        prism_art = Text.from_markup("""
[bold #FF6B6B]██████╗ [/][bold #FF8E53]██████╗ [/][bold #FFC107]██╗[/][bold #4CAF50]███████╗[/][bold #2196F3]███╗   ███╗[/]
[bold #FF6B6B]██╔══██╗[/][bold #FF8E53]██╔══██╗[/][bold #FFC107]██║[/][bold #4CAF50]██╔════╝[/][bold #2196F3]████╗ ████║[/]
[bold #FF6B6B]██████╔╝[/][bold #FF8E53]██████╔╝[/][bold #FFC107]██║[/][bold #4CAF50]███████╗[/][bold #2196F3]██╔████╔██║[/]
[bold #FF6B6B]██╔═══╝ [/][bold #FF8E53]██╔══██╗[/][bold #FFC107]██║[/][bold #4CAF50]╚════██║[/][bold #2196F3]██║╚██╔╝██║[/]
[bold #FF6B6B]██║     [/][bold #FF8E53]██║  ██║[/][bold #FFC107]██║[/][bold #4CAF50]███████║[/][bold #2196F3]██║ ╚═╝ ██║[/]
[bold #FF6B6B]╚═╝     [/][bold #FF8E53]╚═╝  ╚═╝[/][bold #FFC107]╚═╝[/][bold #4CAF50]╚══════╝[/][bold #2196F3]╚═╝     ╚═╝[/]""")
        
        # Tagline with gradient
        tagline = Text()
        tagline.append("P", style="bold #FF6B6B")
        tagline.append("rocess · ", style="#FF6B6B")
        tagline.append("R", style="bold #FF8E53")
        tagline.append("efine · ", style="#FF8E53")
        tagline.append("I", style="bold #FFC107")
        tagline.append("ntegrate · ", style="#FFC107")
        tagline.append("S", style="bold #4CAF50")
        tagline.append("ummarize · ", style="#4CAF50")
        tagline.append("M", style="bold #2196F3")
        tagline.append("anage", style="#2196F3")
        
        # Version info
        version_text = Text()
        version_text.append(f"v{self.VERSION} ", style="bold #00D4FF")
        version_text.append(f'"{self.CODENAME}"', style="italic #BD93F9")
        version_text.append(" │ ", style="dim")
        version_text.append("Social Intelligence Analysis System", style="#6272A4")
        
        # Features badges
        features = Text()
        features.append(" 🚀 Parallel Processing ", style="on #2d2d2d")
        features.append(" ", style="")
        features.append(" 🔄 Auto-Resume ", style="on #2d2d2d")
        features.append(" ", style="")
        features.append(" 📊 Multi-Model ", style="on #2d2d2d")
        features.append(" ", style="")
        features.append(" ⚡ Batch API ", style="on #2d2d2d")
        
        # Build the banner using Group for proper centering
        banner_content = Group(
            Align.center(prism_art),
            Text(""),  # Spacer
            Align.center(tagline),
            Align.center(version_text),
            Text(""),  # Spacer
            Align.center(features),
        )
        
        # Create panel
        panel = Panel(
            banner_content,
            border_style="#4a4a4a",
            box=box.DOUBLE,
            padding=(1, 2),
        )
        
        self.console.print()
        self.console.print(panel)
        self.console.print()
    
    def _show_basic_banner(self):
        """Fallback basic banner without rich"""
        banner = """
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║   ██████╗ ██████╗ ██╗███████╗███╗   ███╗                             ║
║   ██╔══██╗██╔══██╗██║██╔════╝████╗ ████║                             ║
║   ██████╔╝██████╔╝██║███████╗██╔████╔██║                             ║
║   ██╔═══╝ ██╔══██╗██║╚════██║██║╚██╔╝██║                             ║
║   ██║     ██║  ██║██║███████║██║ ╚═╝ ██║                             ║
║   ╚═╝     ╚═╝  ╚═╝╚═╝╚══════╝╚═╝     ╚═╝                             ║
║                                                                       ║
║   Process · Refine · Integrate · Summarize · Manage                   ║
║   Social Intelligence Analysis System v5.0 "Orchestrator"             ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
        """
        print(banner)
    
    def select_or_create_project(self, repository):
        """Interactive project selection or creation with styled menu"""
        if RICH_AVAILABLE:
            return self._select_project_rich(repository)
        else:
            return self._select_project_basic(repository)
    
    def _select_project_rich(self, repository):
        """Rich-styled project selection"""
        self.console.print()
        self.console.print(Rule("[bold #00D4FF]📂 PROJECT SELECTION[/]", style="#4a4a4a"))
        self.console.print()
        
        projects = repository.list_projects()
        
        if projects:
            # Create project table
            table = Table(
                show_header=True,
                header_style="bold #BD93F9",
                border_style="#4a4a4a",
                box=box.ROUNDED,
                padding=(0, 1)
            )
            table.add_column("#", style="#6272A4", justify="center", width=4)
            table.add_column("Project Name", style="#00D4FF")
            table.add_column("Status", justify="center", width=12)
            
            for i, project in enumerate(projects, 1):
                # Check if project has input file
                project_path = repository.get_project_path(project)
                has_input = (project_path / "data" / "inputs" / "input.csv").exists()
                status = "[green]● Ready[/]" if has_input else "[yellow]○ No input[/]"
                
                table.add_row(f"[bold]{i}[/]", project, status)
            
            self.console.print(table)
            self.console.print()
            
            # New project option
            self.console.print("  [bold #50FA7B][N][/] [#50FA7B]Create new project[/]")
            self.console.print()
            
            choice = Prompt.ask(
                "[#6272A4]Select project[/]",
                default="1"
            ).strip().upper()
            
            if choice == 'N':
                return self._create_new_project_rich(repository)
            
            try:
                project_idx = int(choice) - 1
                if 0 <= project_idx < len(projects):
                    project_name = projects[project_idx]
                    self.console.print(f"\n[#50FA7B]✓[/] Selected: [bold #00D4FF]{project_name}[/]")
                    return project_name
            except ValueError:
                pass
            
            self.console.print("[#FF5555]⚠ Invalid selection[/]")
            return self._select_project_rich(repository)
        else:
            self.console.print("[#FFB86C]📁 No existing projects found[/]")
            return self._create_new_project_rich(repository)
    
    def _create_new_project_rich(self, repository):
        """Create new project with rich styling"""
        self.console.print()
        project_name = Prompt.ask("[#BD93F9]Enter project name[/]")
        
        if not project_name:
            self.console.print("[#FF5555]⚠ Project name cannot be empty[/]")
            return self._create_new_project_rich(repository)
        
        # Clean project name
        project_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in project_name)
        
        repository.create_project(project_name)
        return project_name
    
    def _select_project_basic(self, repository):
        """Basic project selection fallback"""
        print("\n" + "═" * 70)
        print("  📂 PROJECT SELECTION")
        print("═" * 70)
        
        projects = repository.list_projects()
        
        if projects:
            print("\nExisting projects:")
            for i, project in enumerate(projects, 1):
                print(f"  [{i}] {project}")
            print(f"  [N] Create new project")
            
            choice = input("\nSelect project (number) or 'N' for new: ").strip().upper()
            
            if choice == 'N':
                return self._create_new_project_basic(repository)
            
            try:
                project_idx = int(choice) - 1
                if 0 <= project_idx < len(projects):
                    project_name = projects[project_idx]
                    print(f"✓ Selected: {project_name}")
                    return project_name
            except ValueError:
                pass
            
            print("⚠️  Invalid selection")
            return self._select_project_basic(repository)
        else:
            print("\n📁 No existing projects found")
            return self._create_new_project_basic(repository)
    
    def _create_new_project_basic(self, repository):
        """Basic new project creation fallback"""
        project_name = input("\nEnter project name: ").strip()
        
        if not project_name:
            print("⚠️  Project name cannot be empty")
            return self._create_new_project_basic(repository)
        
        project_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in project_name)
        repository.create_project(project_name)
        return project_name
    
    def select_model(self):
        """Interactive model selection with styled cards"""
        if RICH_AVAILABLE:
            return self._select_model_rich()
        else:
            return self._select_model_basic()
    
    def _select_model_rich(self):
        """Rich-styled model selection with cards"""
        self.console.print()
        self.console.print(Rule("[bold #00D4FF]🤖 MODEL SELECTION[/]", style="#4a4a4a"))
        self.console.print()
        
        models = self.models_config.get('available_models', [])
        
        # Create model cards
        for model in models:
            # Determine tier styling
            tier_colors = {
                'fast': ('#50FA7B', '⚡'),
                'balanced': ('#FFB86C', '⚖️'),
                'quality': ('#BD93F9', '💎'),
                'premium': ('#FF79C6', '👑')
            }
            
            tier = model.get('tier', 'balanced').lower()
            color, icon = tier_colors.get(tier, ('#6272A4', '●'))
            
            # Model card
            card_content = Text()
            card_content.append(f"{icon} ", style=color)
            card_content.append(f"{model['name']}\n", style=f"bold {color}")
            card_content.append(f"   {model['description']}\n", style="#8BE9FD")
            card_content.append(f"   Recommended: ", style="#6272A4")
            card_content.append(f"{model['recommended_for']}", style="#6272A4 italic")
            
            panel = Panel(
                card_content,
                title=f"[bold {color}][{model['id']}][/]",
                title_align="left",
                border_style=color,
                box=box.ROUNDED,
                padding=(0, 1)
            )
            
            self.console.print(panel)
        
        self.console.print()
        
        # Selection prompt
        while True:
            try:
                choice = Prompt.ask(
                    f"[#6272A4]Select model[/]",
                    default="1"
                ).strip()
                
                if choice == "":
                    selected = models[0]
                else:
                    model_id = int(choice)
                    selected = next((m for m in models if m['id'] == model_id), None)
                
                if selected:
                    self.console.print(f"\n[#50FA7B]✓[/] Selected: [bold #00D4FF]{selected['name']}[/]")
                    return selected
                
                self.console.print(f"[#FF5555]⚠ Please enter a number between 1 and {len(models)}[/]")
            except ValueError:
                self.console.print("[#FF5555]⚠ Invalid input. Please enter a number.[/]")
    
    def _select_model_basic(self):
        """Basic model selection fallback"""
        print("\n" + "═" * 70)
        print("  🤖 MODEL SELECTION")
        print("═" * 70)
        
        models = self.models_config.get('available_models', [])
        
        for model in models:
            print(f"  [{model['id']}] {model['name']}")
            print(f"      {model['description']}")
            print(f"      Recommended for: {model['recommended_for']}")
            print()
        
        while True:
            try:
                choice = input(f"Select model (1-{len(models)}) [default: 1]: ").strip()
                
                if choice == "":
                    return models[0]
                
                model_id = int(choice)
                selected = next((m for m in models if m['id'] == model_id), None)
                
                if selected:
                    print(f"✓ Selected: {selected['name']}")
                    return selected
                
                print(f"⚠️  Please enter a number between 1 and {len(models)}")
            except ValueError:
                print("⚠️  Invalid input. Please enter a number.")
    
    def select_batch_size(self):
        """Interactive batch size selection with visual indicators"""
        if RICH_AVAILABLE:
            return self._select_batch_size_rich()
        else:
            return self._select_batch_size_basic()
    
    def _select_batch_size_rich(self):
        """Rich-styled batch size selection"""
        self.console.print()
        self.console.print(Rule("[bold #00D4FF]⚡ BATCH SIZE SELECTION[/]", style="#4a4a4a"))
        self.console.print()
        
        # Info panel
        info = Text()
        info.append("Batch size determines how many rows are processed per API call.\n", style="#8BE9FD")
        info.append("Higher ", style="#6272A4")
        info.append("= Faster but slight accuracy risk", style="#FFB86C")
        info.append(" │ ", style="dim")
        info.append("Lower ", style="#6272A4")
        info.append("= Slower but more accurate", style="#50FA7B")
        
        self.console.print(Panel(info, border_style="#4a4a4a", box=box.ROUNDED))
        self.console.print()
        
        batch_sizes = self.models_config.get('batch_sizes', [])
        
        # Create batch size table
        table = Table(
            show_header=True,
            header_style="bold #BD93F9",
            border_style="#4a4a4a",
            box=box.ROUNDED
        )
        table.add_column("#", style="#6272A4", justify="center", width=4)
        table.add_column("Size", justify="center", width=8)
        table.add_column("Description", style="#8BE9FD")
        table.add_column("Speed", justify="center", width=12)
        
        for i, batch in enumerate(batch_sizes, 1):
            size = batch['size']
            desc = batch['description']
            
            # Speed indicator with visual bar
            if size == 1:
                speed = "[#6272A4]━[/][dim]━━━━[/]"
                speed_text = "1x"
            else:
                multiplier = batch.get('speed_multiplier', 1)
                bars = min(int(multiplier), 5)
                speed = f"[#50FA7B]{'━' * bars}[/][dim]{'━' * (5-bars)}[/]"
                speed_text = f"{multiplier}x"
            
            size_display = f"{size} row{'s' if size > 1 else ''}"
            
            table.add_row(
                f"[bold]{i}[/]",
                size_display,
                desc,
                f"{speed} {speed_text}"
            )
        
        self.console.print(table)
        self.console.print()
        
        while True:
            try:
                choice = Prompt.ask(
                    f"[#6272A4]Select batch size[/]",
                    default="2"
                ).strip()
                
                if choice == "":
                    idx = 1
                else:
                    idx = int(choice) - 1
                
                if 0 <= idx < len(batch_sizes):
                    size = batch_sizes[idx]['size']
                    self.console.print(f"\n[#50FA7B]✓[/] Selected: [bold #00D4FF]{size} row(s) per API call[/]")
                    return size
                
                self.console.print(f"[#FF5555]⚠ Please enter a number between 1 and {len(batch_sizes)}[/]")
            except ValueError:
                self.console.print("[#FF5555]⚠ Invalid input. Please enter a number.[/]")
    
    def _select_batch_size_basic(self):
        """Basic batch size selection fallback"""
        print("\n" + "═" * 70)
        print("  ⚡ BATCH SIZE SELECTION")
        print("═" * 70)
        print("Batch size determines how many rows are processed per API call.")
        print("Higher = Faster but slight accuracy risk | Lower = Slower but more accurate")
        print()
        
        batch_sizes = self.models_config.get('batch_sizes', [])
        
        for i, batch in enumerate(batch_sizes, 1):
            size = batch['size']
            desc = batch['description']
            
            if size == 1:
                print(f"  [{i}] {size} row/call  - {desc}")
            else:
                print(f"  [{i}] {size} rows/call - {desc} ({batch['speed_multiplier']}x faster)")
        
        while True:
            try:
                choice = input(f"\nSelect batch size (1-{len(batch_sizes)}) [default: 2]: ").strip()
                
                if choice == "":
                    return batch_sizes[1]['size']
                
                idx = int(choice) - 1
                if 0 <= idx < len(batch_sizes):
                    size = batch_sizes[idx]['size']
                    print(f"✓ Selected: {size} row(s) per API call")
                    return size
                
                print(f"⚠️  Please enter a number between 1 and {len(batch_sizes)}")
            except ValueError:
                print("⚠️  Invalid input. Please enter a number.")
    
    def select_row_range(self, total_rows):
        """Interactive row range selection with visual slider"""
        if RICH_AVAILABLE:
            return self._select_row_range_rich(total_rows)
        else:
            return self._select_row_range_basic(total_rows)
    
    def _select_row_range_rich(self, total_rows):
        """Rich-styled row range selection"""
        self.console.print()
        self.console.print(Rule("[bold #00D4FF]📊 ROW RANGE SELECTION[/]", style="#4a4a4a"))
        self.console.print()
        
        # Dataset info panel
        info = Text()
        info.append("Total rows in dataset: ", style="#6272A4")
        info.append(f"{total_rows:,}", style="bold #00D4FF")
        
        self.console.print(Panel(info, border_style="#4a4a4a", box=box.ROUNDED))
        self.console.print()
        
        # Start row
        while True:
            try:
                start_input = Prompt.ask(
                    f"[#BD93F9]START[/] [#6272A4]row (1-{total_rows:,})[/]",
                    default="1"
                ).strip()
                
                if start_input == "":
                    start_row = 1
                    break
                
                start_row = int(start_input.replace(',', ''))
                if 1 <= start_row <= total_rows:
                    break
                
                self.console.print(f"[#FF5555]⚠ Must be between 1 and {total_rows:,}[/]")
            except ValueError:
                self.console.print("[#FF5555]⚠ Invalid input. Please enter a number.[/]")
        
        self.console.print(f"[#50FA7B]✓[/] Start: Row [bold]{start_row:,}[/]")
        
        # End row
        while True:
            try:
                end_input = Prompt.ask(
                    f"[#BD93F9]END[/] [#6272A4]row ({start_row:,}-{total_rows:,})[/]",
                    default=str(total_rows)
                ).strip()
                
                if end_input == "":
                    end_row = total_rows
                    break
                
                end_row = int(end_input.replace(',', ''))
                if start_row <= end_row <= total_rows:
                    break
                
                self.console.print(f"[#FF5555]⚠ Must be between {start_row:,} and {total_rows:,}[/]")
            except ValueError:
                self.console.print("[#FF5555]⚠ Invalid input. Please enter a number.[/]")
        
        self.console.print(f"[#50FA7B]✓[/] End: Row [bold]{end_row:,}[/]")
        
        # Visual range indicator
        self.console.print()
        range_count = end_row - start_row + 1
        pct = (range_count / total_rows) * 100
        bar_width = 40
        filled = int((range_count / total_rows) * bar_width)
        
        bar = Text()
        bar.append("  [", style="#6272A4")
        bar.append("█" * filled, style="#00D4FF")
        bar.append("░" * (bar_width - filled), style="#4a4a4a")
        bar.append("]", style="#6272A4")
        bar.append(f" {range_count:,} rows ({pct:.1f}%)", style="#8BE9FD")
        
        self.console.print(bar)
        
        return start_row, end_row
    
    def _select_row_range_basic(self, total_rows):
        """Basic row range selection fallback"""
        print("\n" + "═" * 70)
        print("  📊 ROW RANGE SELECTION")
        print("═" * 70)
        print(f"Total rows in dataset: {total_rows}")
        print()
        
        # Start row
        while True:
            try:
                start_input = input(f"START row (1-{total_rows}) [default: 1]: ").strip()
                
                if start_input == "":
                    start_row = 1
                    break
                
                start_row = int(start_input)
                if 1 <= start_row <= total_rows:
                    break
                
                print(f"⚠️  Must be between 1 and {total_rows}")
            except ValueError:
                print("⚠️  Invalid input. Please enter a number.")
        
        print(f"✓ Start: Row {start_row}")
        
        # End row
        while True:
            try:
                end_input = input(f"END row ({start_row}-{total_rows}) [default: {total_rows}]: ").strip()
                
                if end_input == "":
                    end_row = total_rows
                    break
                
                end_row = int(end_input)
                if start_row <= end_row <= total_rows:
                    break
                
                print(f"⚠️  Must be between {start_row} and {total_rows}")
            except ValueError:
                print("⚠️  Invalid input. Please enter a number.")
        
        print(f"✓ End: Row {end_row}")
        
        return start_row, end_row
    
    def show_job_summary(self, config):
        """Display job configuration summary with styled panel"""
        if RICH_AVAILABLE:
            self._show_job_summary_rich(config)
        else:
            self._show_job_summary_basic(config)
    
    def _show_job_summary_rich(self, config):
        """Rich-styled job summary"""
        self.console.print()
        self.console.print(Rule("[bold #00D4FF]📋 JOB SUMMARY[/]", style="#4a4a4a"))
        self.console.print()
        
        # Create summary table
        table = Table(
            show_header=False,
            border_style="#4a4a4a",
            box=box.ROUNDED,
            padding=(0, 1),
            expand=True
        )
        table.add_column("Property", style="#6272A4", width=20)
        table.add_column("Value", style="#00D4FF")
        
        rows_to_process = config['row_count']
        
        table.add_row("Project", f"[bold]{config['project_name']}[/]")
        table.add_row("Model", config['model_name'])
        table.add_row("Batch Size", f"{config['batch_size']} row(s) per API call")
        table.add_row("Row Range", f"{config['start_row']:,} → {config['end_row']:,} [#6272A4]({rows_to_process:,} total)[/]")
        table.add_row("Est. API Calls", f"[#FFB86C]{config['estimated_api_calls']:,}[/]")
        table.add_row("Input", config['input_file'])
        table.add_row("Output", f"[#50FA7B]{config['output_file']}[/]")
        table.add_row("Checkpoint", f"Every {config['checkpoint_interval']} rows")
        
        self.console.print(table)
    
    def _show_job_summary_basic(self, config):
        """Basic job summary fallback"""
        print("\n" + "═" * 70)
        print("  📋 JOB SUMMARY")
        print("═" * 70)
        print(f"  Project: {config['project_name']}")
        print(f"  Model: {config['model_name']}")
        print(f"  Batch Size: {config['batch_size']} row(s) per API call")
        print(f"  Rows: {config['start_row']} to {config['end_row']} ({config['row_count']} total)")
        print(f"  Estimated API calls: {config['estimated_api_calls']}")
        print(f"  Input: {config['input_file']}")
        print(f"  Output: {config['output_file']}")
        print(f"  Checkpoint interval: {config['checkpoint_interval']} rows")
        print("═" * 70)
    
    def confirm_start(self):
        """Confirm job start with styled prompt"""
        if RICH_AVAILABLE:
            self.console.print()
            return Confirm.ask("[bold #50FA7B]▶ Start job?[/]", default=True)
        else:
            confirm = input("\n▶️  Start job? (y/n) [y]: ").lower().strip()
            return confirm != 'n'
    
    def confirm_resume(self, last_row):
        """Confirm resuming from checkpoint"""
        if RICH_AVAILABLE:
            self.console.print()
            return Confirm.ask(
                f"[#FFB86C]🔄 Resume from Row {last_row + 1:,}?[/]",
                default=True
            )
        else:
            resume = input(f"\nResume from Row {last_row + 1}? (y/n) [y]: ").lower().strip()
            return resume != 'n'
    
    def show_completion_message(self):
        """Display job completion message with celebration"""
        if RICH_AVAILABLE:
            self._show_completion_rich()
        else:
            self._show_completion_basic()
    
    def _show_completion_rich(self):
        """Rich-styled completion message"""
        self.console.print()
        
        # Celebration content
        content = Text()
        content.append("🎉 ", style="")
        content.append("JOB COMPLETE", style="bold #50FA7B")
        content.append(" 🎉\n\n", style="")
        content.append("All processing finished successfully!\n", style="#8BE9FD")
        content.append("Check the output and analytics files for results.", style="#6272A4")
        
        panel = Panel(
            Align.center(content),
            border_style="#50FA7B",
            box=box.DOUBLE,
            padding=(1, 4)
        )
        
        self.console.print(panel)
        self.console.print()
    
    def _show_completion_basic(self):
        """Basic completion message fallback"""
        completion = """
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║                        ✅ JOB COMPLETE                                ║
║                                                                       ║
║   All processing finished successfully!                               ║
║   Check the output and analytics files for results.                   ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
        """
        print(completion)
    
    def show_mode_selector(self):
        """Show mode selection: Interactive vs Automated"""
        if not RICH_AVAILABLE:
            return 'interactive'
        
        self.console.print()
        self.console.print(Rule("[bold #00D4FF]🎯 SELECT MODE[/]", style="#4a4a4a"))
        self.console.print()
        
        # Mode cards
        modes = [
            {
                'id': 1,
                'name': 'Interactive',
                'icon': '🎮',
                'desc': 'Step-by-step guided processing',
                'features': ['Manual selections', 'Single file', 'Real-time feedback'],
                'color': '#00D4FF'
            },
            {
                'id': 2,
                'name': 'Automated',
                'icon': '🚀',
                'desc': 'Parallel batch processing',
                'features': ['YAML config', 'Multi-file queue', 'N parallel workers'],
                'color': '#BD93F9'
            }
        ]
        
        for mode in modes:
            features_text = " · ".join(mode['features'])
            
            content = Text()
            content.append(f"{mode['icon']} ", style="")
            content.append(f"{mode['name']}\n", style=f"bold {mode['color']}")
            content.append(f"   {mode['desc']}\n", style="#8BE9FD")
            content.append(f"   {features_text}", style="#6272A4")
            
            panel = Panel(
                content,
                title=f"[bold {mode['color']}][{mode['id']}][/]",
                title_align="left",
                border_style=mode['color'],
                box=box.ROUNDED,
                padding=(0, 1)
            )
            
            self.console.print(panel)
        
        self.console.print()
        
        choice = Prompt.ask(
            "[#6272A4]Select mode[/]",
            choices=["1", "2"],
            default="1"
        )
        
        return 'interactive' if choice == "1" else 'automated'
    
    def show_error(self, message):
        """Display styled error message"""
        if RICH_AVAILABLE:
            self.console.print(f"\n[bold #FF5555]❌ ERROR:[/] [#FF5555]{message}[/]")
        else:
            print(f"\n❌ ERROR: {message}")
    
    def show_warning(self, message):
        """Display styled warning message"""
        if RICH_AVAILABLE:
            self.console.print(f"[#FFB86C]⚠ {message}[/]")
        else:
            print(f"⚠️  {message}")
    
    def show_success(self, message):
        """Display styled success message"""
        if RICH_AVAILABLE:
            self.console.print(f"[#50FA7B]✓ {message}[/]")
        else:
            print(f"✓ {message}")
    
    def show_info(self, message):
        """Display styled info message"""
        if RICH_AVAILABLE:
            self.console.print(f"[#8BE9FD]ℹ {message}[/]")
        else:
            print(f"ℹ {message}")
    
    def show_tip(self, message):
        """Display styled tip message"""
        if RICH_AVAILABLE:
            self.console.print(f"[#BD93F9]💡 TIP:[/] [#6272A4]{message}[/]")
        else:
            print(f"💡 TIP: {message}")