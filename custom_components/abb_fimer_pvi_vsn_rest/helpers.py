"""Helper functions."""
import logging

def log_debug(logger: logging.Logger, context: str, message: str, **kwargs):
    """Log debug."""
    extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.debug("%s: %s %s", context, message, extra)

def log_info(logger: logging.Logger, context: str, message: str, **kwargs):
    """Log info."""
    extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info("%s: %s %s", context, message, extra)

def log_warning(logger: logging.Logger, context: str, message: str, **kwargs):
    """Log warning."""
    extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.warning("%s: %s %s", context, message, extra)

def log_error(logger: logging.Logger, context: str, message: str, **kwargs):
    """Log error."""
    extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.error("%s: %s %s", context, message, extra)
