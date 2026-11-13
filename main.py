import io
import json
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from src import (
    MovieStorage,
    MovieUploadInfo,
    MovieDataResponse,
    MovieProcessingReport,
)
from src.storage import MOVIE_COLUMNS
from data_pipeline import create_cleaning_report, process_data, validate_dataframe

setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing API", version="1.0.0")
app.middleware("http")(log_requests)
storage = MovieStorage()

@app.get("/health", response_model=HealthResponse)
def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/upload", response_model=DatasetInfo)
async def upload_dataset(file: UploadFile = File(...)):

    if Path(file.filename or "").suffix.lower() != ".csv":
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported"
        )
    
    contents = await file.read()
    
    try: 
        df = pd.read_csv(io.BytesIO(contents))
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        logger.warning(f"Cannot read CSV due to: {error}")

        raise HTTPException(
            status_code=400,
            detail="Cannot read CSV"
        )
    dataset_id = storage.save(df, file.filename)
    metadata = storage.get_metadata(dataset_id)
    
    logger.info(f"Uploaded dataset: id={dataset_id}, filename={file.filename}, rows={len(df)}")

    return metadata

@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, limit: int = Query(default=100, ge=1)):
    dataset = storage.get(dataset_id)
    if dataset is None:
        logger.warning(f"Dataset not found: {dataset_id}")
        raise HTTPException(status_code=404, detail="Dataset not found")

    records = json.loads(dataset.head(limit).to_json(orient="records"))
    logger.info(f"Retrieved dataset: id={dataset_id}, rows={len(records)}")
    return {"id": dataset_id, "data": records, "total_rows": len(dataset)}

@app.post(
    "/datasets/{dataset_id}/process",
    response_model=ProcessingReport
)
def process_dataset(dataset_id: int, config: ProcessConfig):
    
    """Validate and process a stored dataset using MP1 functions."""
    dataset = storage.get(dataset_id)
    if dataset is None:
        logger.warning(f"Dataset not found: {dataset_id}")
        raise HTTPException(status_code=404, detail="Dataset not found")

    settings = config.model_dump()
    validation = settings["validation"]
    try:
        for column in validation["numeric_columns"]:
            if column not in dataset.columns:
                raise ValueError(f"Numeric column not found: {column}")

        validated = validate_dataframe(
            dataset,
            required_columns=validation["required_columns"],
            numeric_columns=validation["numeric_columns"],
        )
        validation_rows_removed = len(dataset) - len(validated)
        before_processing = validated.copy()
        processed = process_data(validated, settings)
        cleaning_report = create_cleaning_report(before_processing, processed)
    except ValueError as error:
        logger.warning(f"Cannot process dataset: id={dataset_id}, error={error}")
        raise HTTPException(status_code=400, detail=str(error)) from error

    storage.update(dataset_id, processed)
    logger.info(
        f"Processed dataset: id={dataset_id}, "
        f"validation_removed={validation_rows_removed}, "
        f"rows_before={len(before_processing)}, rows_after={len(processed)}"
    )
    return {
        "id": dataset_id,
        "validation_rows_removed": validation_rows_removed,
        "cleaning_report": cleaning_report,
    }
