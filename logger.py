import logging
import sys
import inspect
from urllib3.util.retry import Retry

# Default format for the entire application
DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

def setup_logging(level=logging.INFO):
    """Initializes the global logging configuration."""
    logging.basicConfig(
        level=level,
        format=DEFAULT_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

def get_logger(name: str = None):
    """
    Returns a logger instance. 
    If name is not provided, it automatically detects the caller's module name.
    """
    if name is None:
        # Get the caller's module name
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        name = module.__name__ if module else "__main__"
    
    return logging.getLogger(name)

# Create a logger for this module
logger = get_logger()

class LoggedRetry(Retry):
    """Retry subclass that logs each retry attempt."""

    def increment(self, method=None, url=None, error=None, *args, **kwargs):
        if error:
            logger.warning(
                f"Retry triggered | method={method} url={url} "
                f"error={error} | attempts_left={self.total - 1}"
            )
        return super().increment(method, url, error, *args, **kwargs)
