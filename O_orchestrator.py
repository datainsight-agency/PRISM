"""
O_orchestrator.py - Multi-Instance Job Orchestrator
Hybrid approach: Spawns detached workers, monitors via status files
"""

import os
import sys
import yaml
import json
import time
import signal
import subprocess
import pandas as pd
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from utilities.run_ids import build_run_id, resolve_model_tag

# Optional: Rich for beautiful dashboard
try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
    from rich.layout import Layout
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  'rich' library not found. Install with: pip install rich")
    print("   Falling back to basic console output.\n")


class Orchestrator:
    """
    Main orchestrator for parallel multi-file processing
    Uses hybrid approach: detached subprocesses + file-based status monitoring
    """
    
    def __init__(self, config_path: str, run_id: Optional[str] = None):
        self.config = self.load_config(config_path)
        self.config_path = config_path
        
        # Project metadata
        self.project_name = self.config['project']['name']
        self.version = self.config['project']['version']
        self.model_name = self.config['model']['name']
        self.model_tag = resolve_model_tag(self.model_name)
        self.date_stamp = datetime.now().strftime("%Y%m%d")
        
        # Run-scoped paths and identifiers
        self.reset_run_context(run_id)
        
        # Track workers and results
        self.workers: Dict[int, subprocess.Popen] = {}
        self.worker_configs: Dict[int, dict] = {}
        self.failed_ranges: List[dict] = []
        
        # Console for output
        self.console = Console() if RICH_AVAILABLE else None
        
        # Graceful shutdown
        self.shutdown_requested = False
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
    
    def load_config(self, config_path: str) -> dict:
        """Load YAML configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        print("\n\n⚠️  Shutdown requested. Workers will continue independently.")
        print("   Check status files in status/ directory.")
        print("   Rerun orchestrator to monitor existing workers.\n")
        self.shutdown_requested = True
    
    def reset_run_context(self, run_id: Optional[str] = None):
        """(Re)set run_id and associated directories/metadata."""
        self.run_id = run_id or build_run_id(self.project_name, self.version, self.model_name)
        
        self.status_dir = Path(self.config['monitoring']['status_dir']) / self.run_id
        self.logs_dir = Path(self.config['monitoring']['logs_dir']) / self.run_id
        self.output_dir = Path(self.config['output']['directory']) / self.run_id
        self.checkpoint_dir = Path(self.config['output']['checkpoints']['directory']) / self.run_id
        
        # Keep a copy of run metadata for later resume/monitor-only use
        self.run_metadata_file = self.logs_dir / "run_metadata.json"
        self.run_manifest_file = self.logs_dir / "run_manifest.json"
        self.pause_file = self.status_dir / "pause.flag"
        
        for d in [self.status_dir, self.logs_dir, self.output_dir, self.checkpoint_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        self.persist_run_metadata()
        self.ensure_manifest_initialized()
    
    def persist_run_metadata(self):
        """Persist run metadata to assist with resume/monitoring later."""
        metadata = {
            "project": self.project_name,
            "version": self.version,
            "model_name": self.model_name,
            "model_tag": self.model_tag,
            "run_id": self.run_id,
            "started_at": datetime.now().isoformat(),
            "config_path": str(Path(self.config_path).resolve()),
            "status_dir": str(self.status_dir.resolve()),
            "logs_dir": str(self.logs_dir.resolve()),
            "output_dir": str(self.output_dir.resolve()),
            "checkpoint_dir": str(self.checkpoint_dir.resolve()),
        }
        try:
            self.run_metadata_file.parent.mkdir(parents=True, exist_ok=True)
            if self.run_metadata_file.exists():
                return
            with open(self.run_metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not persist run metadata: {e}")
    
    def manifest_template(self):
        """Base manifest structure."""
        return {
            "run_id": self.run_id,
            "project": self.project_name,
            "version": self.version,
            "model_name": self.model_name,
            "model_tag": self.model_tag,
            "created_at": datetime.now().isoformat(),
            "config_snapshot": self.config,
            "files": []
        }
    
    def ensure_manifest_initialized(self):
        """Create a manifest file if it does not exist."""
        if not self.run_manifest_file.exists():
            try:
                self.run_manifest_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.run_manifest_file, "w", encoding="utf-8") as f:
                    json.dump(self.manifest_template(), f, indent=2)
            except Exception as e:
                print(f"⚠️  Could not initialize run manifest: {e}")
    
    def load_manifest(self) -> dict:
        """Load the current run manifest."""
        if self.run_manifest_file.exists():
            try:
                with open(self.run_manifest_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Could not read manifest: {e}")
        return self.manifest_template()
    
    def save_manifest(self, manifest: dict):
        """Persist manifest to disk."""
        try:
            self.run_manifest_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.run_manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save manifest: {e}")
    
    def update_manifest_for_file(self, label: str, input_file: str, row_ranges: List[dict]):
        """Add or update a file entry with planned row ranges and expected outputs."""
        manifest = self.load_manifest()
        files = manifest.get("files", [])
        
        expected_outputs = [
            str(self.output_dir / self.generate_output_name(label, r.get("worker_id")))
            for r in row_ranges
        ]
        
        file_entry = {
            "label": label,
            "input_file": input_file,
            "status": "pending",
            "row_ranges": row_ranges,
            "expected_outputs": expected_outputs,
            "merged_output": None,
            "last_updated": datetime.now().isoformat()
        }
        
        # Replace or append
        updated = False
        for idx, item in enumerate(files):
            if item.get("label") == label:
                files[idx] = file_entry
                updated = True
                break
        if not updated:
            files.append(file_entry)
        
        manifest["files"] = files
        self.save_manifest(manifest)
    
    def mark_manifest_file_status(self, label: str, status: str, merged_output: Optional[str] = None):
        """Mark a file entry with completion/failed and merged output."""
        manifest = self.load_manifest()
        files = manifest.get("files", [])
        
        for idx, item in enumerate(files):
            if item.get("label") == label:
                item["status"] = status
                if merged_output:
                    item["merged_output"] = merged_output
                item["last_updated"] = datetime.now().isoformat()
                files[idx] = item
                break
        
        manifest["files"] = files
        self.save_manifest(manifest)
    
    def generate_output_name(self, label: str, worker_id: Optional[int] = None) -> str:
        """Generate output filename based on naming pattern"""
        pattern = self.config['output']['naming_pattern']
        
        name = pattern.format(
            project=self.project_name,
            version=self.version,
            label=label,
            date=self.date_stamp,
            run_id=self.run_id
        )
        
        if worker_id is not None:
            name = f"{name}_w{worker_id}"
        
        return f"{name}.csv"
    
    def calculate_row_ranges(self, total_rows: int, num_workers: int) -> List[dict]:
        """Auto-calculate row ranges for parallel processing"""
        rows_per_worker = total_rows // num_workers
        remainder = total_rows % num_workers
        
        ranges = []
        start = 1
        
        for i in range(num_workers):
            extra = 1 if i < remainder else 0
            end = start + rows_per_worker + extra - 1
            ranges.append({
                'start': start, 
                'end': end, 
                'worker_id': i + 1
            })
            start = end + 1
        
        return ranges
    
    def get_row_ranges(self, input_file: str) -> List[dict]:
        """Get row ranges based on configuration"""
        parallelization = self.config['parallelization']
        
        if not parallelization['enabled']:
            df = pd.read_csv(input_file)
            return [{'start': 1, 'end': len(df), 'worker_id': 1}]
        
        strategy = parallelization['split_strategy']
        num_workers = parallelization['workers']
        
        if strategy == 'manual':
            ranges = parallelization['manual_ranges'].copy()
            for i, r in enumerate(ranges):
                r['worker_id'] = i + 1
            return ranges
        
        elif strategy == 'auto':
            df = pd.read_csv(input_file)
            return self.calculate_row_ranges(len(df), num_workers)
        
        else:
            raise ValueError(f"Unknown split strategy: {strategy}")
    
    def clear_status_files(self):
        """Clear previous status files"""
        if not self.status_dir.exists():
            return
        for f in self.status_dir.glob("worker_*.json"):
            try:
                f.unlink()
            except Exception:
                pass
    
    def spawn_worker(self, input_file: str, label: str, row_range: dict) -> subprocess.Popen:
        """Spawn a detached worker process"""
        worker_id = row_range['worker_id']
        
        # Create project path for worker logs
        project_path = Path('projects') / f"{self.project_name}_{self.version}" / self.run_id
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Build command
        cmd = [
            sys.executable, "W_worker.py",
            "--worker-id", str(worker_id),
            "--input-file", input_file,
            "--row-start", str(row_range['start']),
            "--row-end", str(row_range['end']),
            "--model", self.config['model']['name'],
            "--batch-size", str(self.config['model']['batch_size']),
            "--prompts-config", self.config['prompts']['config_file'],
            "--output-dir", str(self.output_dir),
            "--output-name", self.generate_output_name(label, worker_id),
            "--checkpoint-dir", str(self.checkpoint_dir),
            "--checkpoint-interval", str(self.config['output']['checkpoints']['interval']),
            "--status-dir", str(self.status_dir),
            "--pause-file", str(self.pause_file),
            "--project-path", str(project_path),
            "--run-id", self.run_id,
            "--retries", str(self.config['model']['retries']),
            "--delay", str(self.config['model'].get('delay', 5))
        ]
        
        # Spawn detached process
        # stdout/stderr go to log files via W_worker.py
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True  # Detach from parent
        )
        
        # Store config for potential retry
        self.worker_configs[worker_id] = {
            'input_file': input_file,
            'label': label,
            'row_range': row_range,
            'cmd': cmd
        }
        
        return process
    
    def read_worker_status(self, worker_id: int) -> Optional[dict]:
        """Read worker status from file"""
        status_file = self.status_dir / f"worker_{worker_id}.json"
        
        if not status_file.exists():
            return None
        
        try:
            with open(status_file, 'r') as f:
                return json.load(f)
        except:
            return None
    
    def get_all_worker_statuses(self) -> Dict[int, dict]:
        """Get status of all workers"""
        statuses = {}
        for worker_id in self.workers.keys():
            status = self.read_worker_status(worker_id)
            if status:
                statuses[worker_id] = status
        return statuses
    
    def print_basic_status(self, statuses: Dict[int, dict]):
        """Print status without rich library"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(f"\n{'='*70}")
        print(f"  🎯 ORCHESTRATOR - {self.project_name} {self.version}")
        print(f"  Run ID: {self.run_id}")
        print(f"{'='*70}\n")
        
        for worker_id, status in sorted(statuses.items()):
            state = status.get('state', 'unknown')
            progress = status.get('progress_pct', 0)
            rows = status.get('rows_processed', 0)
            total = status.get('total_rows', 0)
            eta = status.get('eta_seconds')
            
            # State emoji
            state_emoji = {
                'initializing': '🔄',
                'running': '⏳',
                'completed': '✅',
                'failed': '❌'
            }.get(state, '❓')
            
            eta_str = f"{eta/60:.1f}m" if eta else "-"
            
            print(f"  {state_emoji} Worker {worker_id}: {state.upper()}")
            print(f"     Progress: {rows}/{total} ({progress}%)")
            print(f"     ETA: {eta_str}")
            print()
    
    def create_rich_dashboard(self, statuses: Dict[int, dict]) -> Table:
        """Create rich table dashboard"""
        table = Table(title=f"🎯 {self.project_name} {self.version} | Run: {self.run_id}")
        
        table.add_column("Worker", style="cyan", justify="center")
        table.add_column("State", justify="center")
        table.add_column("Progress", justify="right")
        table.add_column("Rows", justify="right")
        table.add_column("API Calls", justify="right")
        table.add_column("ETA", justify="right")
        table.add_column("Errors", justify="center")
        
        for worker_id, status in sorted(statuses.items()):
            state = status.get('state', 'unknown')
            progress = status.get('progress_pct', 0)
            rows_processed = status.get('rows_processed', 0)
            total_rows = status.get('total_rows', 0)
            api_calls = status.get('api_calls', 0)
            eta = status.get('eta_seconds')
            errors = status.get('errors', 0)
            
            # State styling
            state_styles = {
                'initializing': ("[yellow]🔄 INIT[/yellow]"),
                'running': ("[blue]⏳ RUNNING[/blue]"),
                'completed': ("[green]✅ DONE[/green]"),
                'failed': ("[red]❌ FAILED[/red]")
            }
            state_display = state_styles.get(state, f"[grey]{state}[/grey]")
            
            # Progress bar
            progress_bar = f"[{'█' * int(progress/5)}{'░' * (20-int(progress/5))}] {progress}%"
            
            # ETA
            eta_str = f"{eta/60:.1f}m" if eta else "-"
            
            # Errors styling
            errors_display = f"[red]{errors}[/red]" if errors > 0 else "[green]0[/green]"
            
            table.add_row(
                f"W{worker_id}",
                state_display,
                progress_bar,
                f"{rows_processed}/{total_rows}",
                str(api_calls),
                eta_str,
                errors_display
            )
        
        return table
    
    def monitor_workers(self):
        """Monitor workers until all complete or fail"""
        refresh_rate = self.config['monitoring']['dashboard_refresh']
        
        while not self.shutdown_requested:
            statuses = self.get_all_worker_statuses()
            
            if not statuses:
                time.sleep(1)
                continue
            
            # Check if all workers are done
            all_done = all(
                s.get('state') in ['completed', 'failed'] 
                for s in statuses.values()
            )
            
            # Display status
            if RICH_AVAILABLE and self.console:
                os.system('clear' if os.name == 'posix' else 'cls')
                table = self.create_rich_dashboard(statuses)
                self.console.print(table)
                self.console.print("\n[dim]Press Ctrl+C to detach (workers continue)[/dim]")
            else:
                self.print_basic_status(statuses)
            
            if all_done:
                break
            
            time.sleep(refresh_rate)
        
        return self.get_all_worker_statuses()
    
    def collect_results(self, statuses: Dict[int, dict]) -> dict:
        """Collect and analyze results from all workers"""
        results = {
            'successful': [],
            'failed': [],
            'total_rows': 0,
            'total_errors': 0,
            'output_files': []
        }
        
        for worker_id, status in statuses.items():
            if status.get('state') == 'completed':
                results['successful'].append(worker_id)
                results['total_rows'] += status.get('rows_processed', 0)
                if status.get('output_file'):
                    results['output_files'].append(status['output_file'])
            
            elif status.get('state') == 'failed':
                results['failed'].append(worker_id)
                results['total_errors'] += 1
                
                # Track failed range for retry
                config = self.worker_configs.get(worker_id, {})
                self.failed_ranges.append({
                    'worker_id': worker_id,
                    'row_range': config.get('row_range', {}),
                    'error': status.get('last_error', 'Unknown error'),
                    'label': config.get('label', '')
                })
        
        return results
    
    def save_failed_ranges(self):
        """Save failed ranges for later retry"""
        if self.failed_ranges:
            failed_file = Path('failed_ranges.json')
            
            # Load existing if present
            existing = []
            if failed_file.exists():
                try:
                    with open(failed_file, 'r') as f:
                        existing = json.load(f)
                except:
                    pass
            
            # Add new failures
            existing.extend(self.failed_ranges)
            
            with open(failed_file, 'w') as f:
                json.dump(existing, f, indent=2)
            
            print(f"\n📝 Failed ranges saved to: {failed_file}")
    
    def merge_outputs(self, label: str, output_files: List[str]) -> Optional[str]:
        """Merge worker outputs into single file"""
        if not output_files:
            print("⚠️  No output files to merge")
            return None
        
        print(f"\n📦 Merging {len(output_files)} output files...")
        
        dfs = []
        for f in sorted(output_files):
            if Path(f).exists():
                try:
                    df = pd.read_csv(f)
                    dfs.append(df)
                    print(f"   ✓ {Path(f).name}: {len(df)} rows")
                except Exception as e:
                    print(f"   ✗ Error reading {f}: {e}")
        
        if not dfs:
            print("⚠️  No valid files to merge")
            return None
        
        # Merge and sort
        merged_df = pd.concat(dfs, ignore_index=True)
        sort_col = self.config['merge'].get('sort_by', 'RowID')
        if sort_col in merged_df.columns:
            merged_df = merged_df.sort_values(sort_col).reset_index(drop=True)
        
        # Generate merged filename
        merged_name = self.generate_output_name(label)
        merged_path = self.output_dir / merged_name
        
        merged_df.to_csv(merged_path, index=False)
        print(f"✅ Merged output: {merged_name} ({len(merged_df)} total rows)")
        
        return str(merged_path)
    
    def retry_failed_workers(self, label: str) -> bool:
        """Retry failed workers"""
        if not self.failed_ranges:
            return True
        
        max_retries = self.config['error_handling'].get('max_worker_retries', 2)
        
        print(f"\n🔄 Retrying {len(self.failed_ranges)} failed worker(s)...")
        
        retry_workers = {}
        for failed in self.failed_ranges:
            worker_id = failed['worker_id']
            config = self.worker_configs.get(worker_id)
            
            if config:
                process = self.spawn_worker(
                    config['input_file'],
                    config['label'],
                    config['row_range']
                )
                retry_workers[worker_id] = process
                print(f"   🚀 Respawned Worker {worker_id}")
        
        if retry_workers:
            self.workers = retry_workers
            self.failed_ranges = []  # Clear for this retry round
            
            # Monitor retried workers
            statuses = self.monitor_workers()
            results = self.collect_results(statuses)
            
            return len(results['failed']) == 0
        
        return False
    
    def prompt_user_on_failure(self, results: dict, label: str) -> str:
        """Prompt user for action on failure"""
        print(f"\n{'='*70}")
        print("⚠️  SOME WORKERS FAILED")
        print(f"{'='*70}")
        print(f"   Successful: {len(results['successful'])}")
        print(f"   Failed: {len(results['failed'])}")
        print()
        
        for failed in self.failed_ranges:
            print(f"   ❌ Worker {failed['worker_id']}: rows {failed['row_range'].get('start')}-{failed['row_range'].get('end')}")
            print(f"      Error: {failed['error'][:100]}...")
        
        print(f"\n{'─'*70}")
        print("Options:")
        print("  [R] Retry failed ranges now")
        print("  [M] Merge successful results only")
        print("  [S] Save state and exit (retry later)")
        print(f"{'─'*70}")
        
        while True:
            choice = input("\nChoice [R/M/S]: ").strip().upper()
            if choice in ['R', 'M', 'S']:
                return choice
            print("Invalid choice. Enter R, M, or S.")
    
    def process_file(self, input_file: str, label: str, row_ranges_override: Optional[List[dict]] = None) -> dict:
        """Process a single input file with parallel workers"""
        print(f"\n{'='*70}")
        print(f"📁 Processing: {input_file}")
        print(f"   Label: {label}")
        print(f"{'='*70}")
        
        # Verify file exists
        if not Path(input_file).exists():
            print(f"❌ File not found: {input_file}")
            return {'status': 'file_not_found'}
        
        # Clear previous status files
        self.clear_status_files()
        
        # Get row ranges
        row_ranges = row_ranges_override or self.get_row_ranges(input_file)
        num_workers = len(row_ranges)
        
        # Persist manifest entry for this file/ranges
        self.update_manifest_for_file(label, input_file, row_ranges)
        
        print(f"   Workers: {num_workers}")
        for r in row_ranges:
            print(f"   • Worker {r['worker_id']}: rows {r['start']}-{r['end']}")
        
        # Spawn workers
        print(f"\n🚀 Spawning {num_workers} worker(s)...\n")
        
        for r in row_ranges:
            process = self.spawn_worker(input_file, label, r)
            self.workers[r['worker_id']] = process
            print(f"   ✓ Worker {r['worker_id']} spawned (PID: {process.pid})")
        
        # Brief pause for workers to initialize
        time.sleep(2)
        
        # Monitor workers
        print("\n📊 Monitoring workers...\n")
        statuses = self.monitor_workers()
        
        if self.shutdown_requested:
            return {'status': 'detached', 'message': 'Orchestrator detached, workers continuing'}
        
        # Collect results
        results = self.collect_results(statuses)
        
        # Handle failures
        if results['failed']:
            if self.config['error_handling'].get('save_failed_ranges', True):
                self.save_failed_ranges()
            
            if self.config['error_handling'].get('prompt_on_failure', True):
                choice = self.prompt_user_on_failure(results, label)
                
                if choice == 'R':
                    # Retry failed workers
                    success = self.retry_failed_workers(label)
                    if success:
                        # Re-collect results
                        statuses = self.get_all_worker_statuses()
                        results = self.collect_results(statuses)
                
                elif choice == 'S':
                    return {'status': 'saved', 'failed_ranges': self.failed_ranges}
                
                # choice == 'M' falls through to merge
        
        # Merge if configured
        merged_file = None
        merge_config = self.config['merge']
        
        if merge_config.get('auto_merge', True):
            condition = merge_config.get('condition', 'all_success')
            
            should_merge = (
                (condition == 'all_success' and len(results['failed']) == 0) or
                (condition == 'any_success' and len(results['successful']) > 0) or
                (condition == 'always')
            )
            
            if should_merge and results['output_files']:
                merged_file = self.merge_outputs(label, results['output_files'])
        
        # Update manifest status
        status_label = "completed" if len(results['failed']) == 0 else "completed_with_failures"
        self.mark_manifest_file_status(label, status_label, merged_output=merged_file)
        
        return {
            'status': 'completed',
            'successful_workers': results['successful'],
            'failed_workers': results['failed'],
            'total_rows': results['total_rows'],
            'merged_file': merged_file,
            'output_files': results['output_files']
        }
    
    def run(self) -> dict:
        """Main orchestration loop"""
        start_time = time.time()
        
        print("\n" + "="*70)
        print("🎯 ORCHESTRATOR STARTED")
        print("="*70)
        print(f"   Project: {self.project_name}")
        print(f"   Version: {self.version}")
        print(f"   Run ID: {self.run_id}")
        print(f"   Model: {self.config['model']['name']}")
        print(f"   Batch size: {self.config['model']['batch_size']}")
        print(f"   Workers: {self.config['parallelization']['workers']}")
        print("="*70)
        
        input_queue = self.config['input_queue']
        
        print(f"\n📋 Input Queue: {len(input_queue)} file(s)")
        for i, item in enumerate(input_queue, 1):
            print(f"   {i}. {item['path']} ({item['label']})")
        
        all_results = {}
        
        # Process each file in queue
        for i, item in enumerate(input_queue, 1):
            file_path = item['path']
            label = item['label']
            
            print(f"\n{'─'*70}")
            print(f"📄 File {i}/{len(input_queue)}: {label}")
            print(f"{'─'*70}")
            
            result = self.process_file(file_path, label)
            all_results[label] = result
            
            if self.shutdown_requested:
                break
        
        # Mark any files not processed as pending in manifest
        manifest = self.load_manifest()
        manifest_labels = {f.get("label") for f in manifest.get("files", [])}
        for item in input_queue:
            if item['label'] not in manifest_labels:
                self.update_manifest_for_file(item['label'], item['path'], [])
        
        # Final summary
        elapsed = time.time() - start_time
        self.print_summary(all_results, elapsed)
        
        return all_results
    
    def run_resume(self, manifest: Optional[dict] = None) -> dict:
        """
        Resume a previously started run using its manifest.
        Only processes files whose status is not 'completed'.
        """
        manifest = manifest or self.load_manifest()
        files = manifest.get("files", [])
        
        if not files:
            print("⚠️  No manifest entries found for this run_id.")
            return {}
        
        start_time = time.time()
        all_results = {}
        
        for entry in files:
            label = entry.get("label")
            status = entry.get("status", "pending")
            input_file = entry.get("input_file")
            
            if status == "completed":
                print(f"⏭️  Skipping {label}: already completed.")
                continue
            
            if not input_file or not Path(input_file).exists():
                print(f"❌ File not found for label {label}: {input_file}")
                self.mark_manifest_file_status(label, "input_missing")
                all_results[label] = {'status': 'file_not_found'}
                continue
            
            row_ranges = entry.get("row_ranges") or self.get_row_ranges(input_file)
            result = self.process_file(input_file, label, row_ranges_override=row_ranges)
            all_results[label] = result
            
            if self.shutdown_requested:
                break
        
        elapsed = time.time() - start_time
        self.print_summary(all_results, elapsed)
        return all_results
    
    def summarize_run(self, manifest: Optional[dict] = None):
        """Print a concise summary for the current run."""
        manifest = manifest or self.load_manifest()
        
        print("\n" + "="*70)
        print("📋 RUN SUMMARY (manifest)")
        print("="*70)
        print(f"Run ID: {manifest.get('run_id', self.run_id)}")
        print(f"Project: {manifest.get('project', self.project_name)}")
        print(f"Version: {manifest.get('version', self.version)}")
        print(f"Model: {manifest.get('model_name', self.model_name)}")
        
        files = manifest.get("files", [])
        if not files:
            print("No file entries recorded.")
        else:
            for entry in files:
                label = entry.get("label")
                status = entry.get("status", "pending")
                merged = entry.get("merged_output")
                expected = entry.get("expected_outputs", [])
                print(f"\n- {label}: {status}")
                print(f"  Input: {entry.get('input_file')}")
                print(f"  Row ranges: {len(entry.get('row_ranges', []))} chunk(s)")
                if merged:
                    print(f"  Merged: {Path(merged).name if isinstance(merged, str) else merged}")
                else:
                    missing_outputs = [p for p in expected if not Path(p).exists()]
                    if expected:
                        print(f"  Expected worker outputs: {len(expected)}")
                        if missing_outputs:
                            print(f"  Missing outputs: {len(missing_outputs)}")
        
        # Current worker statuses (if any)
        statuses = self.get_all_worker_statuses()
        if statuses:
            print("\nCurrent worker states:")
            for worker_id, status in sorted(statuses.items()):
                state = status.get('state', 'unknown')
                progress = status.get('progress_pct', 0)
                rows = status.get('rows_processed', 0)
                total = status.get('total_rows', 0)
                print(f"  Worker {worker_id}: {state} {rows}/{total} ({progress}%)")
        print("="*70 + "\n")
    
    def print_summary(self, all_results: dict, elapsed: float):
        """Print final summary"""
        print("\n" + "="*70)
        print("📊 ORCHESTRATION COMPLETE")
        print("="*70)
        print(f"   Total time: {elapsed/60:.1f} minutes")
        print(f"   Files processed: {len(all_results)}")
        
        total_rows = 0
        total_failed = 0
        
        for label, result in all_results.items():
            status = result.get('status', 'unknown')
            rows = result.get('total_rows', 0)
            failed = len(result.get('failed_workers', []))
            merged = result.get('merged_file', '')
            
            total_rows += rows
            total_failed += failed
            
            status_emoji = '✅' if status == 'completed' and failed == 0 else '⚠️' if failed > 0 else '❌'
            print(f"\n   {status_emoji} {label}:")
            print(f"      Status: {status}")
            print(f"      Rows: {rows}")
            if failed:
                print(f"      Failed workers: {failed}")
            if merged:
                print(f"      Output: {Path(merged).name}")
        
        print(f"\n{'─'*70}")
        print(f"   Total rows processed: {total_rows}")
        if total_failed:
            print(f"   Total failures: {total_failed}")
        print("="*70)


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Job Orchestrator for parallel processing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python O_orchestrator.py job_config.yaml
  python O_orchestrator.py job_config.yaml --dry-run
  python O_orchestrator.py job_config.yaml --workers 6
  python O_orchestrator.py job_config.yaml --version v2
        """
    )
    
    parser.add_argument('config', help='Path to job_config.yaml')
    parser.add_argument('--dry-run', action='store_true', 
                        help='Show execution plan without running')
    parser.add_argument('--workers', type=int, 
                        help='Override number of workers')
    parser.add_argument('--version', type=str, 
                        help='Override version tag')
    parser.add_argument('--monitor-only', action='store_true',
                        help='Only monitor existing workers (no spawn)')
    parser.add_argument('--run-id', type=str,
                        help='Use an explicit run_id (monitor/resume existing run)')
    parser.add_argument('--resume', action='store_true',
                        help='Resume a previous run using its manifest (requires --run-id)')
    parser.add_argument('--summary', action='store_true',
                        help='Print a manifest-based summary for a run (requires --run-id)')
    parser.add_argument('--pause-run', action='store_true',
                        help='Create a pause flag for a run (requires --run-id)')
    parser.add_argument('--resume-run', action='store_true',
                        help='Remove pause flag for a run (requires --run-id)')
    
    args = parser.parse_args()
    
    # Load and optionally override config
    orchestrator = Orchestrator(args.config, run_id=args.run_id)
    
    if args.workers:
        orchestrator.config['parallelization']['workers'] = args.workers
    if args.version:
        orchestrator.version = args.version
    
    # Rebuild run context if overrides change identifiers
    if args.version and not args.run_id:
        orchestrator.reset_run_context()
    elif args.run_id:
        orchestrator.reset_run_context(args.run_id)
    
    # Summary only
    if args.summary:
        if not args.run_id:
            print("❌ --summary requires --run-id")
            return
        manifest = orchestrator.load_manifest()
        orchestrator.summarize_run(manifest)
        return
    
    # Pause/resume flag management
    if args.pause_run:
        if not args.run_id:
            print("❌ --pause-run requires --run-id")
            return
        orchestrator.pause_file.parent.mkdir(parents=True, exist_ok=True)
        orchestrator.pause_file.write_text("paused")
        print(f"⏸️  Pause flag created for run {args.run_id} at {orchestrator.pause_file}")
        return
    
    if args.resume_run:
        if not args.run_id:
            print("❌ --resume-run requires --run-id")
            return
        if orchestrator.pause_file.exists():
            orchestrator.pause_file.unlink()
            print(f"▶️  Pause flag removed for run {args.run_id}")
        else:
            print("ℹ️  No pause flag found.")
        return
    
    # Resume mode
    if args.resume:
        if not args.run_id:
            print("❌ --resume requires --run-id")
            return
        
        manifest = orchestrator.load_manifest()
        # Sync config/project/version from manifest snapshot if present
        if manifest.get("config_snapshot"):
            orchestrator.config = manifest["config_snapshot"]
        if manifest.get("project"):
            orchestrator.project_name = manifest["project"]
        if manifest.get("version"):
            orchestrator.version = manifest["version"]
        if manifest.get("model_name"):
            orchestrator.model_name = manifest["model_name"]
            orchestrator.model_tag = resolve_model_tag(orchestrator.model_name)
        
        orchestrator.reset_run_context(args.run_id)
        orchestrator.run_resume(manifest)
        return
    
    # Dry run
    if args.dry_run:
        print("\n🔍 DRY RUN - Execution Plan:\n")
        print(f"   Project: {orchestrator.project_name}")
        print(f"   Version: {orchestrator.version}")
        print(f"   Model: {orchestrator.config['model']['name']}")
        print(f"   Batch size: {orchestrator.config['model']['batch_size']}")
        print()
        
        for item in orchestrator.config['input_queue']:
            print(f"📁 {item['path']} ({item['label']})")
            if Path(item['path']).exists():
                ranges = orchestrator.get_row_ranges(item['path'])
                for r in ranges:
                    rows = r['end'] - r['start'] + 1
                    print(f"   Worker {r['worker_id']}: rows {r['start']}-{r['end']} ({rows} rows)")
            else:
                print(f"   ⚠️  File not found!")
            print()
        return
    
    # Monitor only mode
    if args.monitor_only:
        print("\n📊 Monitor-only mode: Watching existing workers...\n")
        
        # If no run_id provided, try to pick the most recent status run folder
        if not args.run_id and not orchestrator.status_dir.exists():
            base_status_dir = Path(orchestrator.config['monitoring']['status_dir'])
            candidates = sorted([p for p in base_status_dir.iterdir() if p.is_dir()], reverse=True)
            if candidates:
                orchestrator.reset_run_context(candidates[0].name)
                print(f"ℹ️  Auto-selected latest run_id: {orchestrator.run_id}")
        
        # Find existing worker status files
        for f in orchestrator.status_dir.glob("worker_*.json"):
            worker_id = int(f.stem.split('_')[1])
            orchestrator.workers[worker_id] = None  # No process, just monitoring
        
        if orchestrator.workers:
            orchestrator.monitor_workers()
        else:
            print("No active workers found in status directory.")
        return
    
    # Normal run
    orchestrator.run()


if __name__ == "__main__":
    main()
