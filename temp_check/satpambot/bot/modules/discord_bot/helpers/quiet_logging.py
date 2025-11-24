# -*- coding: utf-8 -*-
"""Configuration overlay to control logging behavior"""
from __future__ import annotations

import logging
from typing import Set

# Channel yang tidak perlu di-log
QUIET_CHANNELS: Set[int] = {
    1400375184048787566,  # Log channel yang disebutkan
}

class QuietChannelFilter(logging.Filter):
    """Filter untuk menyembunyikan log dari channel tertentu"""
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            # Check if log message contains channel ID
            for channel_id in QUIET_CHANNELS:
                if str(channel_id) in record.getMessage():
                    return False
        except:
            pass
        return True

# Setup filter
def setup_logging():
    """Setup logging filters"""
    root_logger = logging.getLogger()
    quiet_filter = QuietChannelFilter()
    root_logger.addFilter(quiet_filter)
    
    # Set specific loggers to higher level
    logging.getLogger('selfheal').setLevel(logging.WARNING)
    logging.getLogger('periodic').setLevel(logging.WARNING)
    
    # Disable specific log categories completely
    for logger_name in ['selfhealnote', 'selfheal.plan']:
        logging.getLogger(logger_name).disabled = True