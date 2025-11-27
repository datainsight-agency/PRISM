"""
R_repository.py - Repository Management Module
Handles project structure, file operations, and path management
"""

import os
import json
from pathlib import Path
from datetime import datetime


class Repository:
    """Manages project directory structure and file operations"""
    
    def __init__(self, base_dir="projects"):
        self.base_dir = Path(base_dir)
        self.config_dir = Path("config")
        self.settings = self._load_settings()
        
    def _load_settings(self):
        """Load settings from config file"""
        settings_path = self.config_dir / "settings.json"
        if settings_path.exists():
            with open(settings_path, 'r') as f:
                return json.load(f)
        return {}
    
    def create_project(self, project_name):
        """Create a new project with standard directory structure"""
        project_path = self.base_dir / project_name
        
        if project_path.exists():
            print(f"📁 Project '{project_name}' already exists")
            return project_path
        
        print(f"\n🔨 Creating project: {project_name}")
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Create standard structure
        structure = self.settings.get('project_structure', {})
        for folder, subfolders in structure.items():
            folder_path = project_path / folder
            folder_path.mkdir(exist_ok=True)
            print(f"  ✓ Created: /{folder}")
            
            for subfolder in subfolders:
                subfolder_path = folder_path / subfolder
                subfolder_path.mkdir(exist_ok=True)
                print(f"    ✓ Created: /{folder}/{subfolder}")
        
        # Create README
        readme_path = project_path / "README.md"
        with open(readme_path, 'w') as f:
            f.write(f"# {project_name}\n\n")
            f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Project Structure\n\n")
            f.write("- `data/inputs/` - Place input CSV files here\n")
            f.write("- `data/outputs/` - Processed results are saved here\n")
            f.write("- `checkpoints/` - Automatic checkpoint saves\n")
            f.write("- `logs/` - Terminal logs and run summaries\n")
            f.write("- `analytics/` - Performance analytics and reports\n")
        
        print(f"  ✓ Created: README.md")
        print(f"\n✅ Project '{project_name}' created successfully!\n")
        
        return project_path
    
    def get_project_path(self, project_name):
        """Get the path to a project directory"""
        return self.base_dir / project_name
    
    def list_projects(self):
        """List all existing projects"""
        if not self.base_dir.exists():
            return []
        
        projects = [p.name for p in self.base_dir.iterdir() if p.is_dir()]
        return sorted(projects)
    
    def get_input_path(self, project_name, filename="input.csv"):
        """Get path to input file"""
        return self.get_project_path(project_name) / "data" / "inputs" / filename
    
    def get_output_path(self, project_name, filename):
        """Get path to output file"""
        return self.get_project_path(project_name) / "data" / "outputs" / filename
    
    def get_checkpoint_dir(self, project_name):
        """Get checkpoint directory path"""
        return self.get_project_path(project_name) / "checkpoints"
    
    def get_log_path(self, project_name, log_type="terminal_logs"):
        """Get log directory path"""
        return self.get_project_path(project_name) / "logs" / log_type
    
    def get_analytics_path(self, project_name):
        """Get analytics directory path"""
        return self.get_project_path(project_name) / "analytics"
    
    def ensure_directories(self, project_name):
        """Ensure all required directories exist"""
        project_path = self.get_project_path(project_name)
        
        if not project_path.exists():
            return False
        
        # Ensure all subdirectories exist
        dirs_to_check = [
            self.get_checkpoint_dir(project_name),
            self.get_log_path(project_name, "terminal_logs"),
            self.get_log_path(project_name, "summaries"),
            self.get_analytics_path(project_name)
        ]
        
        for directory in dirs_to_check:
            directory.mkdir(parents=True, exist_ok=True)
        
        return True
    
    def validate_input_file(self, project_name, filename="input.csv"):
        """Check if input file exists and is valid"""
        input_path = self.get_input_path(project_name, filename)
        
        if not input_path.exists():
            return False, f"Input file not found: {input_path}"
        
        # Could add more validation here (CSV format, required columns, etc.)
        return True, str(input_path)
    
    def get_run_id(self):
        """Generate a unique run ID based on timestamp"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def get_versioned_filename(self, base_name, extension, version_info, run_id=None):
        """
        Generate a versioned filename with metadata.
        If run_id is provided, it is used as the core identifier to keep names consistent across modes.
        """
        extension = extension.lstrip('.')
        
        if run_id:
            row_range = version_info.get('row_range')
            range_suffix = f"_{row_range}" if row_range else ""
            prefix = f"{base_name}" if base_name else ""
            return f"{prefix}{run_id}{range_suffix}.{extension}"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Extract version components
        model_id = version_info.get('model_id', 'unknown')
        batch_size = version_info.get('batch_size', 'unknown')
        row_range = version_info.get('row_range', 'unknown')
        
        filename = f"{base_name}_v{timestamp}_m{model_id}_b{batch_size}_r{row_range}.{extension}"
        return filename
