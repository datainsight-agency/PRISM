#!/usr/bin/env python3
"""
runner.py - PRISM Single Process Main Orchestrator
Process · Refine · Integrate · Summarize · Manage
"""

import sys
import json
import pandas as pd
from pathlib import Path

# Import PRISM modules
from R_repository import Repository
from I_interface import Interface
from P_processor import Processor
from S_serializer import Serializer
from M_monitor import Monitor
from utilities.run_ids import build_run_id


def load_config(filename):
    """Load a JSON configuration file"""
    config_path = Path("config") / filename
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


def main():
    """Main entry point for PRISM"""
    
    # Initialize interface
    interface = Interface()
    interface.show_banner()
    
    # Initialize repository
    repository = Repository()
    
    # Project selection/creation
    project_name = interface.select_or_create_project(repository)
    project_path = repository.get_project_path(project_name)
    
    # Ensure project structure
    if not repository.ensure_directories(project_name):
        print("❌ ERROR: Could not initialize project directories")
        return
    
    # Check for input file
    is_valid, input_path = repository.validate_input_file(project_name)
    if not is_valid:
        print(f"❌ ERROR: {input_path}")
        print(f"\n💡 TIP: Place your input CSV file at:")
        print(f"   {repository.get_input_path(project_name)}")
        return
    
    # Load input data
    print(f"\n📂 LOADING DATA")
    print("-" * 70)
    try:
        df = pd.read_csv(input_path)
        print(f"✓ Loaded: {Path(input_path).name}")
        print(f"✓ Total rows: {len(df)}")
    except Exception as e:
        print(f"❌ ERROR: Could not load input file: {e}")
        return
    
    # Validate required columns
    settings = load_config("settings.json")
    required_cols = settings.get('required_input_columns', ['RowID', 'Message', 'Sentiment'])
    
    if not all(col in df.columns for col in required_cols):
        print(f"❌ ERROR: Input CSV must contain columns: {required_cols}")
        return
    
    # Model selection
    selected_model = interface.select_model()
    model_name = selected_model['name']
    model_id = selected_model['id']
    
    # Batch size selection
    batch_size = interface.select_batch_size()
    
    # Row range selection
    total_rows = len(df)
    start_row, end_row = interface.select_row_range(total_rows)
    
    # Prepare data slice
    start_index = start_row - 1
    end_index = end_row
    df_to_process = df.iloc[start_index:end_index].copy()
    row_count = len(df_to_process)
    
    # Generate job identifiers (run_id encodes project + version tag + model tag)
    version_label = settings.get('interactive_version', 'manual')
    run_id = build_run_id(project_name, version_label, model_name)
    job_id = f"{start_row}-{end_row}_m{model_id}_b{batch_size}_{run_id}"
    
    # Generate output filename (run-scoped, includes row range)
    output_filename = repository.get_versioned_filename(
        base_name="",
        extension="csv",
        version_info={'row_range': f"r{start_row}-{end_row}"},
        run_id=run_id
    )
    output_path = repository.get_output_path(project_name, output_filename)
    
    # Calculate estimated API calls
    estimated_api_calls = (row_count // batch_size) + (1 if row_count % batch_size else 0)
    
    # Prepare job config
    checkpoint_interval = settings.get('checkpoint_interval', 50)
    
    job_config = {
        'project_name': project_name,
        'model_name': model_name,
        'model_id': model_id,
        'batch_size': batch_size,
        'start_row': start_row,
        'end_row': end_row,
        'row_count': row_count,
        'estimated_api_calls': estimated_api_calls,
        'input_file': Path(input_path).name,
        'output_file': output_filename,
        'checkpoint_interval': checkpoint_interval,
        'run_id': run_id,
        'job_id': job_id
    }
    
    # Show summary
    interface.show_job_summary(job_config)
    
    # Confirm start
    if not interface.confirm_start():
        print("❌ Job cancelled")
        return
    
    # Initialize components
    print("\n🔧 INITIALIZING COMPONENTS")
    print("-" * 70)
    
    # Load prompts config
    prompts_config = load_config("prompts.json")
    
    # Initialize processor
    try:
        processor = Processor(
            model_name,
            prompts_config,
            retries=settings.get('retry_attempts', 3),
            delay=settings.get('retry_delay_seconds', 5)
        )
        print("✓ Processor initialized")
    except Exception as e:
        print(f"❌ ERROR: Could not initialize processor: {e}")
        return
    
    # Initialize serializer
    checkpoint_dir = repository.get_checkpoint_dir(project_name) / run_id
    serializer = Serializer(checkpoint_dir, checkpoint_interval)
    print("✓ Serializer initialized")
    
    # Initialize monitor
    monitor = Monitor(project_path, run_id, enable_logging=True)
    print("✓ Monitor initialized")
    
    # Check for checkpoint resume
    df_remaining, last_row_id, has_checkpoint = serializer.get_resume_point(job_id, df_to_process)
    
    if has_checkpoint:
        if interface.confirm_resume(last_row_id):
            df_to_process = df_remaining
            print(f"✓ Resuming from Row {last_row_id + 1}")
            print(f"✓ {len(df_to_process)} rows remaining")
        else:
            print("✓ Starting fresh")
    
    # Check if already complete
    if len(df_to_process) == 0:
        print("\n✅ All rows already processed! Merging checkpoints...")
        if serializer.merge_checkpoints(job_id, output_path):
            print("✅ Job complete")
            interface.show_completion_message()
        return
    
    # Start processing
    print("\n" + "═" * 70)
    print("  🚀 STARTING PROCESSING")
    print("═" * 70)
    
    monitor.start(len(df_to_process))
    
    # Process data
    metadata = {
        'Model_Name': model_name,
        'Batch_Size': batch_size,
        'Run_ID': run_id
    }
    
    try:
        results, api_calls = processor.process_dataframe(
            df_to_process,
            batch_size,
            monitor,
            serializer,
            job_id,
            metadata
        )
        
        # Update final metrics
        job_config['actual_api_calls'] = api_calls
        
    except KeyboardInterrupt:
        monitor.log("\n\n⚠️  Job interrupted by user")
        monitor.log("💾 Checkpoints have been saved. You can resume this job later.")
        monitor.finish()
        return
    except Exception as e:
        monitor.log(f"\n\n❌ FATAL ERROR: {e}")
        monitor.finish()
        return
    
    # Merge checkpoints
    monitor.log("\n📦 Merging checkpoints into final output...")
    
    if serializer.merge_checkpoints(job_id, output_path):
        monitor.log(f"✅ Final output saved: {output_filename}")
        
        # Create analytics
        try:
            final_df = pd.read_csv(output_path)
            monitor.create_analytics(final_df, job_config)
        except Exception as e:
            monitor.log(f"⚠️  Could not create analytics: {e}")
    
    # Finish monitoring
    final_metrics = monitor.finish()
    
    # Show completion
    interface.show_completion_message()
    
    print(f"\n📁 Project location: {project_path}")
    print(f"📊 Output file: data/outputs/{output_filename}")
    print(f"📈 Analytics: analytics/analytics_{run_id}.csv")
    print(f"📝 Log file: logs/terminal_logs/run_{run_id}.log")
    print(f"📄 Summary: logs/summaries/summary_{run_id}.md\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Program interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ UNEXPECTED ERROR: {e}")
        sys.exit(1)
