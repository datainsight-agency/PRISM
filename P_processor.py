"""
P_processor.py - Processing Engine Module
Handles AI model interactions, batch processing, and data transformation
"""

import ollama
import json
import time
import pandas as pd
from pathlib import Path


class Processor:
    """Handles AI model interactions and data processing"""
    
    def __init__(self, model_name, prompts_config, retries=3, delay=5):
        self.model_name = model_name
        self.prompts_config = prompts_config
        self.retries = retries
        self.delay = delay
        
        # Track token and timing stats for throughput reporting
        self._stats = {
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0,
            'total_duration_ns': 0
        }
        
        # Load prompts and validation rules
        self.system_prompt = prompts_config.get('system_prompt', '')
        self.validation_rules = prompts_config.get('validation_rules', {})
        self.columns_to_code = prompts_config.get('columns_to_code', [])
        self.not_applicable_defaults = prompts_config.get('not_applicable_defaults', {})
        
        # Initialize Ollama client
        try:
            self.client = ollama.Client()
            self.client.list()
            print("✓ Ollama connection successful")
        except Exception as e:
            raise ConnectionError(f"Could not connect to Ollama: {e}")
    
    def _record_stats(self, response):
        """Aggregate token counts and durations from an Ollama response."""
        prompt_tokens = response.get('prompt_eval_count') or response.get('prompt_tokens') or 0
        completion_tokens = response.get('eval_count') or response.get('completion_tokens') or 0
        total_tokens = prompt_tokens + completion_tokens
        
        # Prefer total_duration; fall back to prompt/eval durations
        total_duration_ns = response.get('total_duration')
        if total_duration_ns is None:
            total_duration_ns = (response.get('prompt_eval_duration') or 0) + (response.get('eval_duration') or 0)
        
        self._stats['prompt_tokens'] += prompt_tokens
        self._stats['completion_tokens'] += completion_tokens
        self._stats['total_tokens'] += total_tokens
        self._stats['total_duration_ns'] += total_duration_ns or 0
    
    def _build_metrics(self, current_rows, start_time):
        """Compute throughput-style metrics for progress and checkpoints."""
        elapsed = max(time.time() - start_time, 1e-9)
        rows_per_sec = current_rows / elapsed
        
        total_tokens = self._stats['total_tokens']
        duration_sec = (self._stats['total_duration_ns'] or 0) / 1e9
        tokens_per_sec = (total_tokens / duration_sec) if duration_sec > 0 else None
        avg_tokens_per_row = (total_tokens / current_rows) if current_rows > 0 else None
        
        return {
            'elapsed_sec': elapsed,
            'rows_per_sec': rows_per_sec,
            'tokens_total': total_tokens,
            'tokens_per_sec': tokens_per_sec,
            'avg_tokens_per_row': avg_tokens_per_row
        }
    
    def get_single_user_prompt(self, row):
        """Format prompt for single row processing"""
        title = row.get('Title', '')
        title_text = f"Title: {title}\n" if title and str(title).strip() and str(title) != 'nan' else ""
        
        return f"""
Classify this mention:

RowID: {row['RowID']}
[INPUT SENTIMENT]: {row['Sentiment']} ← Validate and override if wrong

{title_text}Content: {row['Message']}
"""
    
    def get_batch_user_prompt(self, rows):
        """Format prompt for batch processing"""
        batch_prompt = f"Classify these {len(rows)} mentions. Return a JSON ARRAY with one object per mention in the EXACT order given.\n\n"
        
        for idx, (_, row) in enumerate(rows.iterrows(), 1):
            title = row.get('Title', '')
            title_text = f"Title: {title}\n" if title and str(title).strip() and str(title) != 'nan' else ""
            
            batch_prompt += f"""
═══════════════════════════════════════════════════════════════════
[MENTION {idx} of {len(rows)}]
RowID: {row['RowID']}
[INPUT SENTIMENT]: {row['Sentiment']} ← Validate and override if wrong

{title_text}Content: {row['Message']}
═══════════════════════════════════════════════════════════════════

"""
        
        batch_prompt += f"\n**RETURN:** A JSON array with EXACTLY {len(rows)} objects in order: [{'{...}'}, {'{...}'}, ...]"
        return batch_prompt
    
    def process_single_row(self, row):
        """Process a single row (traditional method)"""
        user_prompt = self.get_single_user_prompt(row)
        
        for attempt in range(self.retries):
            try:
                response = self.client.chat(
                    model=self.model_name,
                    messages=[
                        {'role': 'system', 'content': self.system_prompt},
                        {'role': 'user', 'content': user_prompt}
                    ],
                    format='json'
                )
                
                # Track token/timing stats for throughput reporting
                self._record_stats(response)
                
                json_string = response['message']['content']
                
                # Clean the JSON string first
                json_string = json_string.strip()
                
                # Try direct parsing first (most reliable)
                try:
                    data_dict = json.loads(json_string)
                except json.JSONDecodeError:
                    # Fallback: Extract JSON manually
                    start_index = json_string.find('{')
                    end_index = json_string.rfind('}')
                    
                    if start_index == -1 or end_index == -1:
                        raise json.JSONDecodeError("No valid JSON found", json_string, 0)
                    
                    cleaned_json_string = json_string[start_index : end_index + 1]
                    
                    try:
                        data_dict = json.loads(cleaned_json_string)
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Row {row['RowID']}: JSON parse error")
                        print(f"   Error: {e}")
                        print(f"   Response preview: {json_string[:200]}")
                        raise
                
                # Handle NOT_APPLICABLE - check first column in columns_to_code
                first_column = self.columns_to_code[0] if self.columns_to_code else None
                if first_column and data_dict.get(first_column) == 'NOT_APPLICABLE':
                    return self.not_applicable_defaults
                
                # Extract required columns
                processed_data = {}
                for col in self.columns_to_code:
                    processed_data[col] = data_dict.get(col, "ERROR_MISSING_KEY")
                
                return self.validate_processed_data(processed_data, row['RowID'])
            
            except Exception as e:
                if attempt < self.retries - 1:
                    print(f"⚠️  Row {row['RowID']}: Attempt {attempt + 1} failed - {e}")
                    time.sleep(self.delay * (attempt + 1))
                    continue
                else:
                    print(f"❌ Row {row['RowID']}: All retries failed - {e}")
                    return {col: "ERROR_ALL_RETRIES_FAILED" for col in self.columns_to_code}
    
    def process_batch(self, rows):
        """Process multiple rows in a single API call"""
        batch_size = len(rows)
        user_prompt = self.get_batch_user_prompt(rows)
        
        for attempt in range(self.retries):
            try:
                response = self.client.chat(
                    model=self.model_name,
                    messages=[
                        {'role': 'system', 'content': self.system_prompt},
                        {'role': 'user', 'content': user_prompt}
                    ],
                    format='json'
                )
                
                # Track token/timing stats for throughput reporting
                self._record_stats(response)
                
                json_string = response['message']['content']
                
                # Clean the JSON string
                json_string = json_string.strip()
                
                # Try direct parsing first
                try:
                    results_array = json.loads(json_string)
                    # If it's a dict, wrap it in array
                    if isinstance(results_array, dict):
                        results_array = [results_array]
                except json.JSONDecodeError:
                    # Fallback: Try to find JSON array manually
                    start_index = json_string.find('[')
                    end_index = json_string.rfind(']')
                    
                    if start_index == -1 or end_index == -1:
                        # Maybe it returned a single object instead of array
                        start_index = json_string.find('{')
                        end_index = json_string.rfind('}')
                        if start_index != -1 and end_index != -1:
                            cleaned = json_string[start_index : end_index + 1]
                            try:
                                single_result = json.loads(cleaned)
                                results_array = [single_result]
                            except json.JSONDecodeError as e:
                                print(f"⚠️  Batch JSON parse error")
                                print(f"   Error: {e}")
                                print(f"   Response preview: {json_string[:300]}")
                                raise
                        else:
                            print(f"⚠️  Batch response preview: {json_string[:300]}")
                            raise json.JSONDecodeError("No valid JSON array or object found", json_string, 0)
                    else:
                        cleaned = json_string[start_index : end_index + 1]
                        try:
                            results_array = json.loads(cleaned)
                        except json.JSONDecodeError as e:
                            print(f"⚠️  Batch JSON parse error")
                            print(f"   Error: {e}")
                            print(f"   Cleaned JSON preview: {cleaned[:300]}")
                            raise
                
                # Validate we got the right number of results
                if len(results_array) != batch_size:
                    print(f"⚠️  WARNING: Expected {batch_size} results, got {len(results_array)}")
                    
                    # If we got fewer results, pad with errors
                    while len(results_array) < batch_size:
                        results_array.append({col: "ERROR_BATCH_MISMATCH" for col in self.columns_to_code})
                    
                    # If we got more results, truncate
                    results_array = results_array[:batch_size]
                
                # Process each result
                processed_results = []
                for i, (idx, row) in enumerate(rows.iterrows()):
                    result = results_array[i]
                    
                    # Handle NOT_APPLICABLE - check first column dynamically
                    first_column = self.columns_to_code[0] if self.columns_to_code else None
                    if first_column and result.get(first_column) == 'NOT_APPLICABLE':
                        processed_results.append(self.not_applicable_defaults)
                    else:
                        processed_data = {}
                        for col in self.columns_to_code:
                            processed_data[col] = result.get(col, "ERROR_MISSING_KEY")
                        
                        processed_results.append(self.validate_processed_data(processed_data, row['RowID']))
                
                return processed_results
            
            except Exception as e:
                if attempt < self.retries - 1:
                    print(f"⚠️  Batch processing attempt {attempt + 1} failed: {e}")
                    time.sleep(self.delay * (attempt + 1))
                    continue
                else:
                    print(f"❌ Batch failed all retries. Falling back to single-row processing.")
                    # Fallback: process each row individually
                    fallback_results = []
                    for idx, row in rows.iterrows():
                        result = self.process_single_row(row)
                        fallback_results.append(result)
                    return fallback_results
    
    def validate_processed_data(self, processed_data, row_id):
        """
        Validate and clean processed data
        ✅ PERMISSIVE: Allows organic labels (with or without brackets)
        ✅ ENFORCES: Conditional logic (e.g., Booking_Related=N → all fields = '-')
        """
        validation_rules = self.validation_rules
        
        # ✅ STEP 1: Enforce conditional logic
        # If first column (e.g., Booking_Related) = 'N', all other fields should be '-'
        first_column = self.columns_to_code[0] if self.columns_to_code else None
        
        if first_column and processed_data.get(first_column) == 'N':
            # Everything else should be '-'
            for col in self.columns_to_code[1:]:  # Skip first column
                current_value = processed_data.get(col, '')
                if current_value not in ['-', 'ERROR_MISSING_KEY']:
                    print(f"⚠️  Row {row_id}: {first_column}=N but {col}='{current_value}' (correcting to '-')")
                    processed_data[col] = '-'
            return processed_data
        
        # ✅ STEP 2: Validate other conditional relationships
        # Check Comparative_Mention → Competitor_Named relationship
        if 'Comparative_Mention' in processed_data and 'Competitor_Named' in processed_data:
            if processed_data['Comparative_Mention'] == 'Y':
                # Must have a competitor name (not 'NONE' or '-')
                if processed_data['Competitor_Named'] in ['NONE', '-', '']:
                    print(f"⚠️  Row {row_id}: Comparative_Mention=Y but no Competitor_Named (setting to 'Other')")
                    processed_data['Competitor_Named'] = 'Other'
            elif processed_data['Comparative_Mention'] == 'N':
                # Should have NONE for competitor and '-' for position
                if processed_data['Competitor_Named'] != 'NONE':
                    print(f"⚠️  Row {row_id}: Comparative_Mention=N but Competitor_Named='{processed_data['Competitor_Named']}' (correcting to 'NONE')")
                    processed_data['Competitor_Named'] = 'NONE'
                if 'Competitive_Position' in processed_data and processed_data['Competitive_Position'] != '-':
                    processed_data['Competitive_Position'] = '-'
        
        # Check Abandonment_Mentioned → Abandonment_Reason relationship
        if 'Abandonment_Mentioned' in processed_data and 'Abandonment_Reason' in processed_data:
            if processed_data['Abandonment_Mentioned'] == 'N':
                if processed_data['Abandonment_Reason'] != 'NONE':
                    print(f"⚠️  Row {row_id}: Abandonment_Mentioned=N but has reason (correcting to 'NONE')")
                    processed_data['Abandonment_Reason'] = 'NONE'
        
        # ✅ STEP 3: Permissive validation - allow organic labels
        for col in self.columns_to_code:
            col_lower = col.lower()
            
            # Try multiple naming patterns for validation rules
            possible_keys = [
                f"valid_{col_lower}",
                f"valid_{col_lower}s",
                f"{col_lower}_valid",
                f"{col_lower}_options"
            ]
            
            # Find matching validation rule
            valid_values = None
            for key in possible_keys:
                if key in validation_rules:
                    valid_values = validation_rules[key]
                    break
            
            # If validation rule exists, check the value
            if valid_values:
                value = processed_data.get(col, '')
                
                # Allow these patterns to pass:
                # 1. Values in the valid list
                # 2. Values wrapped in brackets [Custom_Label]
                # 3. Values that look like custom labels (capitalized with underscores)
                # 4. Already flagged errors
                
                is_in_list = value in valid_values
                is_bracketed = value.startswith('[') and value.endswith(']')
                is_error = value.startswith('ERROR_')
                is_organic_format = '_' in value or value[0].isupper() if value else False
                
                # Only flag as error if:
                # - Not in the valid list
                # - Not bracketed
                # - Not already an error
                # - Not in organic label format
                # - Not a special marker ('-', 'NONE', 'Unknown')
                
                special_markers = ['-', 'NONE', 'Unknown', '']
                
                if (not is_in_list and 
                    not is_bracketed and 
                    not is_error and 
                    value not in special_markers):
                    
                    # This is likely an organic label without brackets
                    # ✅ PERMISSIVE: Just log it, don't flag as error
                    if is_organic_format:
                        print(f"ℹ️  Row {row_id}: Organic label for {col}: '{value}'")
                    else:
                        # Unusual format - might be a typo or model error
                        print(f"⚠️  Row {row_id}: Unexpected value for {col}: '{value}' (allowing as organic)")
        
        return processed_data
    
    def process_dataframe(self, df, batch_size, monitor, serializer, job_id, metadata, pause_event=None):
        """Main processing loop for entire dataframe"""
        results = []
        row_indices = list(df.index)
        total_rows = len(df)
        api_call_count = 0
        start_time = time.time()
        
        # ✅ FIX: Track last checkpoint position instead of using modulo
        last_checkpoint_row = 0
        checkpoint_counter = 0  # Track actual checkpoint number
        
        # Process in batches
        for i in range(0, len(row_indices), batch_size):
            batch_indices = row_indices[i:i + batch_size]
            batch_df = df.loc[batch_indices]
            
            # Cooperative pause: wait while pause_event signals pause
            if pause_event:
                pause_logged = False
                while pause_event():
                    if not pause_logged:
                        try:
                            monitor.log("⏸️  Paused... waiting to resume.", to_console=True)
                        except Exception:
                            pass
                        pause_logged = True
                    time.sleep(1)
                if pause_logged:
                    try:
                        monitor.log("▶️  Resuming processing.", to_console=True)
                    except Exception:
                        pass
            
            if batch_size == 1:
                # Single row processing
                row = batch_df.iloc[0]
                processed_data = self.process_single_row(row)
                batch_results = [processed_data]
            else:
                # Batch processing
                batch_results = self.process_batch(batch_df)
            
            results.extend(batch_results)
            api_call_count += 1
            
            current_row_num = len(results)
            metrics = self._build_metrics(current_row_num, start_time)
            
            # Checkpoint logic
            if serializer.should_checkpoint(current_row_num, total_rows):
                # Push a progress update so monitor/status files stay fresh even between sparse updates
                monitor.update_progress(current_row_num, total_rows, api_call_count, metrics)
                
                # ✅ FIX: Calculate results since LAST checkpoint
                new_results_count = current_row_num - last_checkpoint_row
                
                if new_results_count > 0:
                    checkpoint_results = results[-new_results_count:]
                    checkpoint_indices = row_indices[last_checkpoint_row:current_row_num]
                    
                    checkpoint_data = serializer.prepare_checkpoint_data(
                        checkpoint_results,
                        checkpoint_indices,
                        df,
                        ['RowID', 'Sentiment']
                    )
                    
                    # ✅ FIX: Use sequential checkpoint counter
                    checkpoint_counter += 1
                    
                    # Include throughput metrics in checkpoint metadata for later analysis
                    checkpoint_metadata = dict(metadata)
                    checkpoint_metadata.update({
                        'Rows_Per_Sec': round(metrics['rows_per_sec'], 4),
                        'Tokens_Per_Sec': round(metrics['tokens_per_sec'], 4) if metrics['tokens_per_sec'] is not None else None,
                        'Avg_Tokens_Per_Row': round(metrics['avg_tokens_per_row'], 4) if metrics['avg_tokens_per_row'] is not None else None,
                        'Tokens_Total': metrics['tokens_total']
                    })
                    
                    checkpoint_file = serializer.save_checkpoint(
                        checkpoint_data,
                        job_id,
                        checkpoint_counter,
                        checkpoint_metadata
                    )
                    
                    monitor.record_checkpoint(checkpoint_counter, checkpoint_file)
                    
                    # ✅ FIX: Update last checkpoint position
                    last_checkpoint_row = current_row_num
            
            # Progress update
            if total_rows > 0:
                update_frequency = max(batch_size, total_rows // 20)
                if (current_row_num % update_frequency == 0) or (current_row_num == total_rows):
                    monitor.update_progress(current_row_num, total_rows, api_call_count, metrics)
        
        return results, api_call_count
