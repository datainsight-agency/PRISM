"""
M_monitor.py - Monitoring & Analytics Module
Handles logging, progress tracking, and performance analytics
"""

import sys
import time
import pandas as pd
from datetime import datetime
from pathlib import Path


class Monitor:
    """Handles logging, progress tracking, and analytics"""
    
    def __init__(self, project_path, run_id, enable_logging=True):
        self.project_path = Path(project_path)
        self.run_id = run_id
        self.enable_logging = enable_logging
        
        self.start_time = None
        self.log_buffer = []
        self.metrics = {
            'total_rows': 0,
            'processed_rows': 0,
            'api_calls': 0,
            'errors': 0,
            'checkpoints': 0
        }
        
        if enable_logging:
            self.log_file_path = self.project_path / "logs" / "terminal_logs" / f"run_{run_id}.log"
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def start(self, total_rows):
        """Start monitoring a job"""
        self.start_time = time.time()
        self.metrics['total_rows'] = total_rows
        self.log("=" * 70)
        self.log(f"  RUN STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"  Run ID: {self.run_id}")
        self.log("=" * 70)
    
    def log(self, message, to_console=True, to_file=True):
        """Log a message to console and/or file"""
        if to_console:
            print(message)
        
        if to_file and self.enable_logging:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] {message}"
            self.log_buffer.append(log_entry)
            
            # Write to file periodically
            if len(self.log_buffer) >= 10:
                self._flush_log()
    
    def _flush_log(self):
        """Write buffered logs to file"""
        if self.log_buffer and self.enable_logging:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write('\n'.join(self.log_buffer) + '\n')
            self.log_buffer = []
    
    def update_progress(self, current_row, total_rows, api_calls=None, metrics=None):
        """Update and display progress"""
        self.metrics['processed_rows'] = current_row
        if api_calls:
            self.metrics['api_calls'] = api_calls
        
        if metrics:
            # Store latest throughput metrics for summary/analytics
            self.metrics['rows_per_sec'] = metrics.get('rows_per_sec')
            self.metrics['tokens_per_sec'] = metrics.get('tokens_per_sec')
            self.metrics['avg_tokens_per_row'] = metrics.get('avg_tokens_per_row')
            self.metrics['tokens_total'] = metrics.get('tokens_total')
        
        percentage = (current_row / total_rows) * 100 if total_rows > 0 else 0
        elapsed = time.time() - self.start_time
        
        # Calculate ETA
        if current_row > 0:
            avg_time_per_row = elapsed / current_row
            rows_remaining = total_rows - current_row
            eta_seconds = avg_time_per_row * rows_remaining
        else:
            eta_seconds = 0
        
        elapsed_str = self._format_time(elapsed)
        eta_str = self._format_time(eta_seconds)
        
        progress_msg = (f"⏳ {current_row}/{total_rows} ({percentage:.1f}%) | "
                       f"Elapsed: {elapsed_str} | ETA: {eta_str}")
        
        if api_calls:
            progress_msg += f" | API calls: {api_calls}"
        if metrics:
            rps = metrics.get('rows_per_sec')
            tps = metrics.get('tokens_per_sec')
            avg_tok = metrics.get('avg_tokens_per_row')
            if rps is not None:
                progress_msg += f" | Rows/s: {rps:.2f}"
            if tps is not None:
                progress_msg += f" | Tok/s: {tps:.2f}"
            if avg_tok is not None:
                progress_msg += f" | Avg tok/row: {avg_tok:.1f}"
        
        self.log(progress_msg)
    
    def record_checkpoint(self, checkpoint_num, checkpoint_file):
        """Record checkpoint creation"""
        self.metrics['checkpoints'] += 1
        self.log(f"\n💾 CHECKPOINT {checkpoint_num} SAVED → {Path(checkpoint_file).name}")
        self.log(f"   Progress: {self.metrics['processed_rows']}/{self.metrics['total_rows']} rows")
    
    def record_error(self, error_msg):
        """Record an error"""
        self.metrics['errors'] += 1
        self.log(f"❌ ERROR: {error_msg}")
    
    def record_warning(self, warning_msg):
        """Record a warning"""
        self.log(f"⚠️  WARNING: {warning_msg}")
    
    def finish(self):
        """Finalize monitoring and create summary"""
        total_time = time.time() - self.start_time
        
        self.log("\n" + "=" * 70)
        self.log("  RUN COMPLETED")
        self.log("=" * 70)
        self.log(f"  Total time: {self._format_time(total_time)}")
        self.log(f"  Rows processed: {self.metrics['processed_rows']}/{self.metrics['total_rows']}")
        self.log(f"  API calls: {self.metrics['api_calls']}")
        self.log(f"  Checkpoints: {self.metrics['checkpoints']}")
        self.log(f"  Errors: {self.metrics['errors']}")
        
        if self.metrics['processed_rows'] > 0:
            avg_time = total_time / self.metrics['processed_rows']
            self.log(f"  Avg time per row: {avg_time:.2f}s")
        
        if self.metrics['api_calls'] > 0:
            avg_api_time = total_time / self.metrics['api_calls']
            self.log(f"  Avg time per API call: {avg_api_time:.2f}s")
        
        self.log("=" * 70 + "\n")
        
        # Flush remaining logs
        self._flush_log()
        
        # Create summary
        self._create_summary(total_time)
        
        return self.metrics
    
    def _create_summary(self, total_time):
        """Create markdown summary of the run"""
        summary_path = self.project_path / "logs" / "summaries" / f"summary_{self.run_id}.md"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(summary_path, 'w') as f:
            f.write(f"# Run Summary - {self.run_id}\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Performance Metrics\n\n")
            f.write(f"- **Total Duration:** {self._format_time(total_time)}\n")
            f.write(f"- **Rows Processed:** {self.metrics['processed_rows']}/{self.metrics['total_rows']}\n")
            f.write(f"- **API Calls:** {self.metrics['api_calls']}\n")
            f.write(f"- **Checkpoints Created:** {self.metrics['checkpoints']}\n")
            f.write(f"- **Errors Encountered:** {self.metrics['errors']}\n\n")
            
            if self.metrics['processed_rows'] > 0:
                avg_time = total_time / self.metrics['processed_rows']
                f.write(f"- **Average Time per Row:** {avg_time:.2f}s\n")
            
            if self.metrics['api_calls'] > 0:
                avg_api_time = total_time / self.metrics['api_calls']
                f.write(f"- **Average Time per API Call:** {avg_api_time:.2f}s\n")
            
            f.write("\n## Status\n\n")
            if self.metrics['processed_rows'] == self.metrics['total_rows']:
                f.write("✅ **Completed successfully**\n")
            else:
                f.write("⚠️  **Partially completed**\n")
        
        self.log(f"📊 Summary saved: {summary_path.name}")
    
    def create_analytics(self, output_df, job_config):
        """Create analytics report from processed data"""
        analytics_path = self.project_path / "analytics" / f"analytics_{self.run_id}.csv"
        analytics_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Basic statistics
            analytics = {
                'run_id': [self.run_id],
                'timestamp': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                'model': [job_config.get('model_name', 'unknown')],
                'batch_size': [job_config.get('batch_size', 'unknown')],
                'total_rows': [len(output_df)],
                'total_time_seconds': [time.time() - self.start_time],
                'api_calls': [self.metrics['api_calls']]
            }
            
            # Dynamically analyze all categorical columns
            # Get distribution for any column that looks categorical (< 50 unique values)
            for col in output_df.columns:
                if col not in ['RowID', 'Message', 'Title', 'Model_Name', 'Batch_Size', 'Run_ID']:
                    unique_count = output_df[col].nunique()
                    if unique_count < 50:  # Likely a categorical column
                        value_counts = output_df[col].value_counts()
                        for value, count in value_counts.items():
                            # Clean column and value names for analytics
                            clean_col = col.lower().replace('_', '')
                            clean_val = str(value).replace(' ', '_').replace('-', '_')
                            analytics[f'{clean_col}_{clean_val}'] = [count]
            
            # Count errors across all columns
            error_count = 0
            for col in output_df.columns:
                if output_df[col].astype(str).str.contains('ERROR', na=False).any():
                    error_count += output_df[col].astype(str).str.contains('ERROR', na=False).sum()
            
            analytics['error_count'] = [error_count]
            
            analytics_df = pd.DataFrame(analytics)
            analytics_df.to_csv(analytics_path, index=False)
            
            self.log(f"📈 Analytics saved: {analytics_path.name}")
            
        except Exception as e:
            self.log(f"⚠️  Could not create analytics: {e}")
    
    @staticmethod
    def _format_time(seconds):
        """Format seconds into HH:MM:SS or MM:SS"""
        seconds = int(seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours:02}:{minutes:02}:{seconds:02}"
        else:
            return f"{minutes:02}:{seconds:02}"
