"""
S_serializer.py - Checkpoint & Data Serialization Module
Handles checkpoint management, data saving, and recovery
"""

import os
import pandas as pd
from pathlib import Path


class Serializer:
    """Manages checkpoint creation, recovery, and data serialization"""
    
    def __init__(self, checkpoint_dir, checkpoint_interval=50):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_interval = checkpoint_interval
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def get_checkpoint_filename(self, job_id, checkpoint_num):
        """Generate checkpoint filename"""
        return self.checkpoint_dir / f"checkpoint_{job_id}_part{checkpoint_num:04d}.csv"
    
    def find_last_checkpoint(self, job_id):
        """Find the most recent checkpoint for a job"""
        checkpoint_files = list(self.checkpoint_dir.glob(f"checkpoint_{job_id}_part*.csv"))
        
        if not checkpoint_files:
            return None, 0
        
        checkpoint_nums = []
        for f in checkpoint_files:
            try:
                num = int(f.stem.split('part')[1])
                checkpoint_nums.append(num)
            except:
                continue
        
        if not checkpoint_nums:
            return None, 0
        
        last_num = max(checkpoint_nums)
        last_file = self.get_checkpoint_filename(job_id, last_num)
        
        try:
            df = pd.read_csv(last_file)
            last_row_id = df['RowID'].iloc[-1]
            return str(last_file), last_row_id
        except Exception as e:
            print(f"⚠️  Could not read checkpoint: {e}")
            return None, 0
    
    def save_checkpoint(self, df_chunk, job_id, checkpoint_num, metadata=None):
        """Save a checkpoint with optional metadata"""
        checkpoint_file = self.get_checkpoint_filename(job_id, checkpoint_num)
        
        # Add metadata columns if provided
        if metadata:
            for key, value in metadata.items():
                df_chunk[key] = value
        
        df_chunk.to_csv(checkpoint_file, index=False)
        return str(checkpoint_file)
    
    def list_checkpoints(self, job_id):
        """List all checkpoints for a job"""
        checkpoint_files = sorted(self.checkpoint_dir.glob(f"checkpoint_{job_id}_part*.csv"))
        return [str(f) for f in checkpoint_files]
    
    def merge_checkpoints(self, job_id, output_path):
        """Merge all checkpoints into final output file"""
        checkpoint_files = self.list_checkpoints(job_id)
        
        if not checkpoint_files:
            print("⚠️  No checkpoint files found to merge")
            return False
        
        print(f"\n📦 Merging {len(checkpoint_files)} checkpoint files...")
        dfs = []
        
        for f in checkpoint_files:
            try:
                df = pd.read_csv(f)
                dfs.append(df)
                print(f"  ✓ Loaded {Path(f).name} ({len(df)} rows)")
            except Exception as e:
                print(f"  ✗ Error loading {Path(f).name}: {e}")
        
        if dfs:
            final_df = pd.concat(dfs, ignore_index=True)
            final_df.to_csv(output_path, index=False)
            print(f"✅ Final output saved: {Path(output_path).name} ({len(final_df)} total rows)")
            return True
        
        return False
    
    def cleanup_checkpoints(self, job_id, keep_merged=True):
        """Delete checkpoint files after successful merge"""
        if not keep_merged:
            checkpoint_files = self.list_checkpoints(job_id)
            
            deleted_count = 0
            for f in checkpoint_files:
                try:
                    os.remove(f)
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠️  Could not delete {f}: {e}")
            
            if deleted_count > 0:
                print(f"🗑️  Cleaned up {deleted_count} checkpoint files")
    
    def get_resume_point(self, job_id, df):
        """Get the dataframe filtered to resume from last checkpoint"""
        last_checkpoint, last_row_id = self.find_last_checkpoint(job_id)
        
        if last_checkpoint:
            print(f"\n🔄 CHECKPOINT FOUND: Last processed Row {last_row_id}")
            print(f"   Checkpoint file: {Path(last_checkpoint).name}")
            
            # Filter dataframe to rows after last processed
            df_remaining = df[df['RowID'] > last_row_id].copy()
            print(f"   Rows remaining: {len(df_remaining)}")
            
            return df_remaining, last_row_id, True
        
        return df, 0, False
    
    def should_checkpoint(self, current_row_count, total_rows):
        """Determine if a checkpoint should be created"""
        return (current_row_count % self.checkpoint_interval == 0 or 
                current_row_count == total_rows)
    
    def prepare_checkpoint_data(self, results, indices, original_df, metadata_cols):
        """Prepare data for checkpoint save"""
        # Create checkpoint dataframe
        checkpoint_df = original_df.loc[indices].copy()
        
        # Add processed results
        results_df = pd.DataFrame(results, index=indices)
        
        # Combine metadata and results
        checkpoint_combined = pd.concat([
            checkpoint_df[metadata_cols].reset_index(drop=True),
            results_df.reset_index(drop=True)
        ], axis=1)
        
        return checkpoint_combined