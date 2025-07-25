# Standard Package Imports
import logging
from logging import getLogger, StreamHandler, Formatter, INFO, DEBUG
from dotenv import load_dotenv
import os


# NOTE THIS FILE SHOULD NOT IMPORT ANY LOCAL MODULES

load_dotenv()

def get_logger(name: str=os.environ["MAIN_LOGGER_NAME"], level: int=DEBUG) -> logging.Logger:
    """
    Get a logger object.
    """
    logger = getLogger(name)
    if not logger.handlers:
        logger_format_str = f"[{name}][%(asctime)s][%(levelname)s]: %(message)s"
        logger.setLevel(level)
        handler = StreamHandler()
        handler.setFormatter(Formatter(logger_format_str))
        logger.addHandler(handler)
    logger.propagate = False
    return logger