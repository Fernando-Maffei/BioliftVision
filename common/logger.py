# logger.py
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from common.paths import logs_dir

class AppLogger:
    def __init__(self, name="powerlifting_app"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Evita logs duplicados
        if not self.logger.handlers:
            self.setup_logging()
    
    def setup_logging(self):
        """Configura o sistema de logging"""
        
        # Estrutura de pastas: logs/YYYY/MM/<tipo>.log
        root_dir = logs_dir()
        now = datetime.now()
        year_dir = os.path.join(root_dir, now.strftime('%Y'))
        month_dir = os.path.join(year_dir, now.strftime('%m'))
        os.makedirs(month_dir, exist_ok=True)
        
        # Formato dos logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para arquivo (com rotação)
        safe_name = self.logger.name.lower().replace(' ', '_')
        log_file = os.path.join(month_dir, f"{safe_name}.log")
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=1024 * 1024,  # 1MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # Handler para console (opcional)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Adiciona handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def get_logger(self):
        return self.logger

# Instância global
app_logger = AppLogger().get_logger()

# Funções de conveniência
def log_info(message, *args, **kwargs):
    """Log de nível INFO com suporte a formatação pelo logging."""
    try:
        app_logger.info(message, *args, **kwargs)
    except Exception:
        # Fallback simples em caso de erro no logger
        print(f"INFO: {message}")

def log_error(message, *args, **kwargs):
    """Log de nível ERROR com suporte a formatação pelo logging."""
    try:
        app_logger.error(message, *args, **kwargs)
    except Exception:
        print(f"ERROR: {message}")

def log_warning(message, *args, **kwargs):
    """Log de nível WARNING com suporte a formatação pelo logging.
    Aceita múltiplos argumentos como no logging padrão.
    """
    try:
        app_logger.warning(message, *args, **kwargs)
    except Exception:
        print(f"WARNING: {message}")

def log_debug(message, *args, **kwargs):
    """Log de nível DEBUG com suporte a formatação pelo logging."""
    try:
        app_logger.debug(message, *args, **kwargs)
    except Exception:
        print(f"DEBUG: {message}")
