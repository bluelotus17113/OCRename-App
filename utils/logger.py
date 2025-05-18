import logging
import sys

_app_logger_instance = None

def get_app_logger(name='OCRenameApp'):
    """Retorna la instancia del logger, configurándola si es la primera vez."""
    global _app_logger_instance
    if _app_logger_instance is None:
        from config import settings # IMPORTANTE: Importar aquí

        logger = logging.getLogger(name)
        
        if logger.hasHandlers():
            logger.handlers.clear()

        log_level_value = settings.LOG_LEVEL if hasattr(settings, 'LOG_LEVEL') else "INFO"
        log_level_attr = getattr(logging, log_level_value.upper(), logging.INFO)
        logger.setLevel(log_level_attr)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - [%(levelname)s] - (%(module)s:%(lineno)d) - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        try:
            log_file_name_value = settings.LOG_FILE_NAME if hasattr(settings, 'LOG_FILE_NAME') else "ocrename_activity.log"
            file_handler = logging.FileHandler(log_file_name_value, mode='a', encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"ADVERTENCIA CRÍTICA (logger): No se pudo configurar el logging a archivo: {e}", file=sys.stderr)
            
        _app_logger_instance = logger
    return _app_logger_instance