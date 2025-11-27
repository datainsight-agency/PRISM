"""
W_worker.py - Standalone Worker Process
Runs independently, writes status to file for orchestrator monitoring

INTEGRATES WITH EXISTING MODULES:
- M_monitor.py for logging and progress tracking
- S_serializer.py for checkpoint management
- P_processor.py for AI processing
"""

import os
import sys
import json
import time
import argparse
import traceback
import pandas as pd
from pathlib import Path
from datetime import datetime

# Import existing PRISM modules
from P_processor import Processor
from S_serializer import Serializer
from M_monitor import Monitor


class WorkerStatus:
    """
    Manages worker status file for orchestrator communication.
    This is ADDITIONAL to M_monitor - it writes JSON status files
    that the orchestrator reads for its dashboard.
    """
    
    def __init__(self, worker_id, status_dir, run_id=None):
        self.worker_id = worker_id
        self.status_file = Path(status_dir) / f"worker_{worker_id}.json"
        self.status_dir = Path(status_dir)
        self.status_dir.mkdir(parents=True, exist_ok=True)
        
        self.status = {
            'worker_id': worker_id,
            'run_id': run_id,
            'state': 'initializing',
            'started_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'row_start': 0,
            'row_end': 0,
            'current_row': 0,
            'rows_processed': 0,
            'total_rows': 0,
            'progress_pct': 0.0,
            'api_calls': 0,
            'rows_per_sec': None,
            'tokens_per_sec': None,
            'avg_tokens_per_row': None,
            'tokens_total': None,
            'errors': 0,
            'last_error': None,
            'output_file': None,
            'checkpoints': [],
            'eta_seconds': None
        }
        self.save()
    
    def update(self, **kwargs):
        """Update status and save to file"""
        self.status.update(kwargs)
        self.status['updated_at'] = datetime.now().isoformat()
        
        if self.status['total_rows'] > 0:
            self.status['progress_pct'] = round(
                (self.status['rows_processed'] / self.status['total_rows']) * 100, 1
            )
        
        self.save()
    
    def save(self):
        """Write status to JSON file"""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(self.status, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save status: {e}")
    
    def set_running(self, row_start, row_end, total_rows):
        """Mark worker as running"""
        self.update(
            state='running',
            row_start=row_start,
            row_end=row_end,
            total_rows=total_rows,
            current_row=row_start
        )
    
    def set_progress(self, current_row, rows_processed, api_calls, eta_seconds=None, metrics=None):
        """Update progress"""
        self.update(
            current_row=current_row,
            rows_processed=rows_processed,
            api_calls=api_calls,
            eta_seconds=eta_seconds
        )
        
        if metrics:
            self.update(
                rows_per_sec=metrics.get('rows_per_sec'),
                tokens_per_sec=metrics.get('tokens_per_sec'),
                avg_tokens_per_row=metrics.get('avg_tokens_per_row'),
                tokens_total=metrics.get('tokens_total')
            )
    
    def add_checkpoint(self, checkpoint_file):
        """Record checkpoint"""
        self.status['checkpoints'].append(checkpoint_file)
        self.save()
    
    def set_error(self, error_msg):
        """Record error"""
        self.status['errors'] += 1
        self.update(last_error=error_msg)
    
    def set_completed(self, output_file, rows_processed):
        """Mark worker as completed successfully"""
        self.update(
            state='completed',
            output_file=output_file,
            rows_processed=rows_processed,
            completed_at=datetime.now().isoformat()
        )
    
    def set_failed(self, error_msg):
        """Mark worker as failed"""
        self.update(
            state='failed',
            last_error=error_msg,
            failed_at=datetime.now().isoformat()
        )


class MonitorBridge:
    """
    Bridge between M_monitor.Monitor and WorkerStatus.
    Wraps the real Monitor and also updates WorkerStatus for orchestrator.
    """
    
    def __init__(self, monitor: Monitor, worker_status: WorkerStatus):
        self.monitor = monitor
        self.worker_status = worker_status
        self.start_time = time.time()
    
    def start(self, total_rows):
        """Start monitoring"""
        self.monitor.start(total_rows)
        self.worker_status.set_running(
            self.worker_status.status['row_start'],
            self.worker_status.status['row_end'],
            total_rows
        )
    
    def update_progress(self, current_row, total_rows, api_calls=None, metrics=None):
        """Update progress in both Monitor and WorkerStatus"""
        # Update real monitor
        self.monitor.update_progress(current_row, total_rows, api_calls, metrics)
        
        # Calculate ETA for worker status
        elapsed = time.time() - self.start_time
        if current_row > 0:
            rate = elapsed / current_row
            remaining = total_rows - current_row
            eta = remaining * rate
        else:
            eta = None
        
        # Update worker status for orchestrator
        self.worker_status.set_progress(
            current_row=current_row,
            rows_processed=current_row,
            api_calls=api_calls or 0,
            eta_seconds=eta,
            metrics=metrics
        )
    
    def record_checkpoint(self, checkpoint_num, checkpoint_file):
        """Record checkpoint in both Monitor and WorkerStatus"""
        self.monitor.record_checkpoint(checkpoint_num, checkpoint_file)
        self.worker_status.add_checkpoint(checkpoint_file)
    
    def record_error(self, error_msg):
        """Record error"""
        self.monitor.record_error(error_msg)
        self.worker_status.set_error(error_msg)
    
    def log(self, message, to_console=True, to_file=True):
        """Pass through to monitor"""
        self.monitor.log(message, to_console, to_file)
    
    def finish(self):
        """Finish monitoring"""
        return self.monitor.finish()


class Worker:
    """Standalone worker that processes a range of rows"""
    
    def __init__(self, config):
        self.config = config
        self.worker_id = config['worker_id']
        self.pause_file = Path(config.get('pause_file', 'pause.flag'))
        
        # Setup project path for Monitor
        self.project_path = Path(config.get('project_path', 'projects/orchestrator_runs'))
        self.project_path.mkdir(parents=True, exist_ok=True)
        
        # Ensure log directories exist
        (self.project_path / "logs" / "terminal_logs").mkdir(parents=True, exist_ok=True)
        (self.project_path / "logs" / "summaries").mkdir(parents=True, exist_ok=True)
        
        # Initialize worker status (for orchestrator communication)
        self.worker_status = WorkerStatus(
            self.worker_id, 
            config.get('status_dir', 'status/'),
            config.get('run_id')
        )
        
        # Generate run ID for this worker
        self.run_id = f"{config.get('run_id', datetime.now().strftime('%Y%m%d_%H%M%S'))}_w{self.worker_id}"
        
        # Initialize real Monitor from M_monitor.py
        self.monitor = Monitor(
            project_path=self.project_path,
            run_id=self.run_id,
            enable_logging=True
        )
        
        # Create bridge that updates both Monitor and WorkerStatus
        self.monitor_bridge = MonitorBridge(self.monitor, self.worker_status)
        
        self.log(f"Worker {self.worker_id} initializing...")
        self.log(f"  Input: {config['input_file']}")
        self.log(f"  Rows: {config['row_start']} - {config['row_end']}")
        self.log(f"  Model: {config['model']}")
    
    def log(self, message):
        """Log via monitor"""
        self.monitor.log(message)
    
    def should_pause(self):
        """Return True if a pause flag is present."""
        return self.pause_file.exists()
    
    def load_data(self):
        """Load and filter input data to assigned row range"""
        self.log(f"Loading data from {self.config['input_file']}...")
        
        df = pd.read_csv(self.config['input_file'])
        
        row_start = self.config['row_start']
        row_end = self.config['row_end']
        
        if 'RowID' in df.columns:
            df_filtered = df[(df['RowID'] >= row_start) & (df['RowID'] <= row_end)].copy()
        else:
            df_filtered = df.iloc[row_start-1:row_end].copy()
            df_filtered['RowID'] = range(row_start, row_start + len(df_filtered))
        
        self.log(f"Loaded {len(df_filtered)} rows (RowID {row_start}-{row_end})")
        
        return df_filtered
    
    def run(self):
        """Main worker execution"""
        start_time = time.time()
        
        try:
            # Load prompts config
            self.log(f"Loading prompts from {self.config['prompts_config']}...")
            with open(self.config['prompts_config'], 'r') as f:
                prompts_config = json.load(f)
            
            # Load data
            df = self.load_data()
            total_rows = len(df)
            
            if total_rows == 0:
                self.log("⚠️  No rows to process!")
                self.worker_status.set_completed(None, 0)
                return {'status': 'success', 'rows_processed': 0}
            
            # Update worker status with row info
            self.worker_status.update(
                row_start=self.config['row_start'],
                row_end=self.config['row_end']
            )
            
            # Start monitoring
            self.monitor_bridge.start(total_rows)
            
            # Initialize processor
            self.log("Initializing processor...")
            processor = Processor(
                model_name=self.config['model'],
                prompts_config=prompts_config,
                retries=self.config.get('retries', 3),
                delay=self.config.get('delay', 5)
            )
            
            # Initialize serializer
            checkpoint_dir = self.config.get('checkpoint_dir', 'checkpoints/')
            checkpoint_interval = self.config.get('checkpoint_interval', 50)
            
            serializer = Serializer(
                checkpoint_dir=checkpoint_dir,
                checkpoint_interval=checkpoint_interval
            )
            
            # Generate job ID
            job_id = f"{self.config['row_start']}-{self.config['row_end']}_w{self.worker_id}_{self.config.get('run_id', '')}"
            
            # Metadata for checkpoints
            metadata = {
                'Model_Name': self.config['model'],
                'Batch_Size': self.config['batch_size'],
                'Worker_ID': self.worker_id,
                'Run_ID': self.config.get('run_id', '')
            }
            
            # Process data using the bridge monitor
            self.log(f"Starting processing with batch_size={self.config['batch_size']}...")
            
            results, api_calls = processor.process_dataframe(
                df=df,
                batch_size=self.config['batch_size'],
                monitor=self.monitor_bridge,  # Use bridge, not raw monitor
                serializer=serializer,
                job_id=job_id,
                metadata=metadata,
                pause_event=self.should_pause
            )
            
            # Merge checkpoints into final output
            output_dir = Path(self.config.get('output_dir', 'output/'))
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_name = self.config.get('output_name', f"output_w{self.worker_id}.csv")
            output_path = output_dir / output_name
            
            self.log("Merging checkpoints...")
            serializer.merge_checkpoints(job_id, str(output_path))
            
            # Calculate stats
            elapsed = time.time() - start_time
            rows_processed = len(results)
            
            self.log(f"\n{'='*50}")
            self.log(f"✅ WORKER {self.worker_id} COMPLETED")
            self.log(f"   Rows processed: {rows_processed}")
            self.log(f"   API calls: {api_calls}")
            self.log(f"   Time: {elapsed/60:.1f} minutes")
            self.log(f"   Output: {output_path}")
            self.log(f"{'='*50}")
            
            # Finish monitoring
            self.monitor_bridge.finish()
            
            # Update final status
            self.worker_status.set_completed(str(output_path), rows_processed)
            
            return {
                'status': 'success',
                'rows_processed': rows_processed,
                'api_calls': api_calls,
                'output_file': str(output_path),
                'elapsed_seconds': elapsed
            }
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.log(f"\n❌ WORKER {self.worker_id} FAILED")
            self.log(f"   Error: {error_msg}")
            self.log(f"   Traceback:\n{traceback.format_exc()}")
            
            self.monitor_bridge.finish()
            self.worker_status.set_failed(error_msg)
            
            return {
                'status': 'failed',
                'error': error_msg,
                'traceback': traceback.format_exc()
            }


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Standalone Worker Process')
    
    parser.add_argument('--worker-id', type=int, required=True,
                        help='Worker ID number')
    parser.add_argument('--input-file', type=str, required=True,
                        help='Input CSV file path')
    parser.add_argument('--row-start', type=int, required=True,
                        help='Starting row number (1-indexed)')
    parser.add_argument('--row-end', type=int, required=True,
                        help='Ending row number (inclusive)')
    parser.add_argument('--model', type=str, required=True,
                        help='Ollama model name')
    parser.add_argument('--batch-size', type=int, default=15,
                        help='Batch size for API calls')
    parser.add_argument('--prompts-config', type=str, required=True,
                        help='Path to prompts JSON config')
    parser.add_argument('--output-dir', type=str, default='output/',
                        help='Output directory')
    parser.add_argument('--output-name', type=str, default=None,
                        help='Output filename')
    parser.add_argument('--checkpoint-dir', type=str, default='checkpoints/',
                        help='Checkpoint directory')
    parser.add_argument('--checkpoint-interval', type=int, default=50,
                        help='Checkpoint interval')
    parser.add_argument('--status-dir', type=str, default='status/',
                        help='Status files directory')
    parser.add_argument('--project-path', type=str, default='projects/orchestrator_runs',
                        help='Project path for logs and analytics')
    parser.add_argument('--run-id', type=str, default=None,
                        help='Run ID for this job')
    parser.add_argument('--retries', type=int, default=3,
                        help='Number of retries for failed batches')
    parser.add_argument('--delay', type=int, default=5,
                        help='Delay between retries')
    parser.add_argument('--pause-file', type=str, default=None,
                        help='Path to a pause flag file (exists = pause processing)')
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    
    # Build config from args
    config = {
        'worker_id': args.worker_id,
        'input_file': args.input_file,
        'row_start': args.row_start,
        'row_end': args.row_end,
        'model': args.model,
        'batch_size': args.batch_size,
        'prompts_config': args.prompts_config,
        'output_dir': args.output_dir,
        'output_name': args.output_name or f"output_w{args.worker_id}.csv",
        'checkpoint_dir': args.checkpoint_dir,
        'checkpoint_interval': args.checkpoint_interval,
        'status_dir': args.status_dir,
        'project_path': args.project_path,
        'run_id': args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S"),
        'retries': args.retries,
        'delay': args.delay,
        'pause_file': args.pause_file or Path(args.status_dir) / "pause.flag"
    }
    
    # Create and run worker
    worker = Worker(config)
    result = worker.run()
    
    # Exit with appropriate code
    sys.exit(0 if result['status'] == 'success' else 1)


if __name__ == "__main__":
    main()
