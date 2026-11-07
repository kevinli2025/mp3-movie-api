def setup_logging(verbose=False):
    """Configure logging for the pipeline."""
    if verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S"
    )  

def validate_input(filepath):
    """Check whether the input path exists and is a file."""
    p = Path(filepath)
    if p.is_file():
        logger.info(f"File validated: '{filepath}'")
        return True
    else:
        logger.error(f"File not found: '{filepath}'")
        return False
    
import logging
from pathlib import Path

logger = logging.getLogger(__name__)