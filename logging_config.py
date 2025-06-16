import logging
import sys

_LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return application logger."""
    logger = logging.getLogger('QISsy')
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger

logger = setup_logging()
