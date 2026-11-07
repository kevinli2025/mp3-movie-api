import logging
from pathlib import Path


logger = logging.getLogger(__name__)


def save_data(df, filepath):
    """Save a DataFrame as a CSV file."""
    output = Path(filepath)
    if not output.parent.exists():
        output.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output, index=False)

    logger.debug(f"rows saved: {len(df)} output path: {output}")
    return output