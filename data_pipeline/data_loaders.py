# data_loaders.py
from pathlib import Path

import logging
import pandas as pd
import json
import yaml


# Do not call logging.basicConfig() here.
# Use the logging configuration from Part 1.
logger = logging.getLogger(__name__)


def load_csv(filepath):
    df = pd.read_csv(filepath)
    logger.info(f"Loaded CSV file: {filepath.name} ({len(df)} rows)")
    return df


def load_json(filepath):
    with open(filepath, "r") as f:
        data = json.load(f)

    logger.info(f"Loaded JSON file: {filepath.name}")
    return data


def load_yaml(filepath):
    with open(filepath, "r") as f:
        config = yaml.safe_load(f)
    
    logger.info(f"Loaded YAML file: {filepath.name}")
    return config


def load_data(filepath):
    p = Path(filepath)
    suffix = p.suffix.lower()
    if suffix == ".csv":
        return load_csv(p)
    elif suffix == ".json":
        return load_json(p)
    elif suffix == ".yaml":
        return load_yaml(p)
    else:
        logger.error(f"Unsupported file format: {suffix}")
        raise ValueError
    