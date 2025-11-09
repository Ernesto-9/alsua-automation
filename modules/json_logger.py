"""
Logging estructurado en formato JSON
Facilita análisis y monitoreo
"""
import json
import logging
import os
from datetime import datetime
from modules.config import LOG_JSON_ENABLED, LOG_DIR

class JSONLogger:
    def __init__(self, name="alsua_system"):
        self.name = name
        self.enabled = LOG_JSON_ENABLED
        if self.enabled:
            os.makedirs(LOG_DIR, exist_ok=True)
            self.log_file = os.path.join(LOG_DIR, f"{name}_{datetime.now().strftime('%Y%m%d')}.jsonl")

    def log(self, level, message, **extra):
        """Log estructurado en JSON"""
        if not self.enabled:
            return

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'logger': self.name,
            'message': message,
            **extra
        }

        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logging.error(f"Error escribiendo log JSON: {e}")

    def info(self, message, **extra):
        self.log('INFO', message, **extra)

    def error(self, message, **extra):
        self.log('ERROR', message, **extra)

    def warning(self, message, **extra):
        self.log('WARNING', message, **extra)

json_logger = JSONLogger()
