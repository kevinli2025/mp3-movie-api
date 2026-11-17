import io
import json
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from src import (
    MovieCache,
    MovieStorage,
    MovieUploadInfo,
    MovieDataResponse,
    MovieProcessingReport,
    HealthResponse,
    ProcessConfig,
    setup_logging,
    log_requests,
)
from src.storage import MOVIE_COLUMNS
from data_pipeline import create_cleaning_report, process_data, validate_dataframe

setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Movie API", version="1.0.0")
app.middleware("http")(log_requests)
storage = MovieStorage()
cache = MovieCache()

@app.get("/health", response_model=HealthResponse)
def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/upload", response_model=MovieUploadInfo)
async def upload_movies(file: UploadFile = File(...)):

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
    
    if set(df.columns) != set(MOVIE_COLUMNS):
        raise HTTPException(
            status_code=400,
            detail="Invalid movie columns"
        )
    
    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="Invalid empty dataset"
        )
    
    df = df[MOVIE_COLUMNS]

    storage.save(df)
    cache.invalidate()
    logger.info(f"filename={file.filename}, rows={len(df)}")

    return {
        "filename" : file.filename,
        "rows" : len(df),
        "columns" : len(df.columns),
        "column_names" : list(df.columns)
    }


@app.get("/movies", response_model=MovieDataResponse)
def get_movies(limit: int = Query(default=100, ge=1)):

    # First, check if the response is already cached
    cached = cache.get(limit)

    if cached is not None:
        logger.info(f"Cache hit for limit={limit}")
        return cached

    # Cache miss: retrieve from SQLite
    records = storage.select_columns(MOVIE_COLUMNS, limit)
    total_rows = storage.count_movies()

    response = {
        "data": records,
        "total_rows": total_rows
    }

    # Save the response for future requests
    cache.set(limit, response)

    logger.info(f"Retrieved movies: returned_rows={len(records)}")
    return response

@app.get("/movies/search", response_model=list[dict])
def query_movies(
    columns: list[str] = Query(default=["title"]),
    min_rating: float = Query(default=0, ge=0, le=10),
    limit: int = Query(default=100, ge=1)
):
    try:
        records = storage.query_movies(columns, min_rating, limit)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        ) from error
    
    logger.info(f"Selected columns: {columns} row count: {len(records)}")
    return records

@app.post("/movies/process", response_model=MovieProcessingReport)
def process_movies(config: ProcessConfig):
    
    dataset = storage.get()
    if dataset.empty:
        logger.warning("No movies to process")
        raise HTTPException(status_code=400, detail="No movies to process")

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
        logger.warning(f"Cannot process movies: error={error}")
        raise HTTPException(status_code=400, detail=str(error)) from error

    storage.save(processed)
    cache.invalidate()

    logger.info(
        f"Processed movies: "
        f"validation_removed={validation_rows_removed}, "
        f"rows_before={len(before_processing)}, rows_after={len(processed)}"
    )
    return {
        "validation_rows_removed": validation_rows_removed,
        "cleaning_report": cleaning_report,
    }