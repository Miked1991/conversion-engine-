"""
Phase 5: Observability
Logs traces to Langfuse for cost and latency tracking
"""

import os
import json
from datetime import datetime
from typing import Dict


async def log_trace(trace_id: str, event_type: str, data: Dict) -> None:
    """
    Send trace to Langfuse (or local file for demo)
    """
    # For interim submission, write to local file
    # In production, use Langfuse SDK
    
    log_entry = {
        'trace_id': trace_id,
        'event_type': event_type,
        'timestamp': datetime.now().isoformat(),
        'data': data
    }
    
    # Append to trace log file
    with open('eval/trace_log.jsonl', 'a') as f:
        f.write(json.dumps(log_entry) + '\n')


def get_logger(name: str):
    """Simple logger for development"""
    import logging
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger