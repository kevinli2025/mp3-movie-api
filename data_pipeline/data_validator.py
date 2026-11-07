import logging
import pandas as pd


logger = logging.getLogger(__name__)


def validate_dataframe(df, required_columns, numeric_columns):
    rows_before = len(df)

    for col in required_columns:
        if col not in df.columns:
            logger.error(f"{col} not in columns")
            raise ValueError
    
    for col in numeric_columns:
        invalid_rows = []
        for i, value in df[col].items():
            if pd.notna(value):
                try:
                    float(value)
                except (ValueError, TypeError):
                    logger.warning(f"invalid numeric value at row {i}")
                    invalid_rows.append(i)

        df = df.drop(index= invalid_rows)
        df[col] = pd.to_numeric(df[col])

    logger.debug(f"validation: {rows_before} -> {len(df)} rows")
    return df
    