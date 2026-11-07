import logging
import pandas as pd

logger = logging.getLogger(__name__)

def remove_duplicates(df):
    prev_len = len(df)
    new_df = df.drop_duplicates()
    after_len = len(new_df)
    logger.debug(f"remove_duplicates: {prev_len} -> {after_len} rows")
    return new_df


def handle_missing(df, axis="rows"):
    if axis == "rows":
        new_df = df.dropna(axis="rows")
        logger.debug(f"handle_missing: {len(df)} -> {len(new_df)}")
    elif axis == "columns":
        new_df = df.dropna(axis="columns")
        logger.debug(f"handle_missing: {len(df.columns)} -> {len(new_df.columns)}")
    else:
        logger.error(f"Unsupported axis")
        raise ValueError
    return new_df


def remove_outliers(df, columns, method, threshold):
    if (method != "iqr") and (method != "zscore"):
        logger.error("invalid method, only 'iqr' and 'zscore' are valid")
        raise ValueError
    for column in columns:
        if column not in list(df):
            logger.warning(f"column {column} does not exist")
            continue
        elif pd.api.types.is_numeric_dtype(df[column]) is False:
            logger.warning(f"column {column} is not numeric")
            continue

        prev_len = len(df)

        if method == "iqr":
            q1 = df[column].quantile(0.25)
            q3 = df[column].quantile(0.75)
            iqr = q3 - q1

            lower = q1 - (threshold * iqr)
            upper = q3 + (threshold * iqr)

            df = df[(df[column] >= lower) & (df[column] <= upper)]

        elif method == "zscore":
            mean = df[column].mean()
            std = df[column].std()

            z_scores = (df[column] - mean) / std
            df = df[abs(z_scores) <= threshold]

        logger.debug(f"{column}: method = {method}, threshold = {threshold}, rows removed = {prev_len - len(df)} ")
    return df
    

def process_data(df, config):
    processing = config["processing"]
    remove_dupes = processing["remove_duplicates"]
    missing = processing["missing"]
    outliers = processing["outliers"]

    if remove_dupes is True:
        df = remove_duplicates(df)

    if missing["enabled"] is True:
        df = handle_missing(df, missing["axis"])

    if outliers["enabled"] is True:
        df = remove_outliers(df, outliers["columns"], outliers["method"], outliers["threshold"])
    
    return df


def create_cleaning_report(df_before, df_after):
    cleaning_report = {"rows_before": len(df_before), 
                       "rows_after": len(df_after),
                       "rows_removed": (len(df_before) - len(df_after)),
                       "columns_before": len(df_before.columns),
                       "columns_after": len(df_after.columns),
                       "columns_removed": (len(df_before.columns) - len(df_after.columns))}
    
    return cleaning_report