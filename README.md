This project is a FastAPI application for uploading, storing, searching, and processing movie data. You can upload CSV files, which are saved in a SQLite database, replacing the previous data. The src/database.py and src/storage.py modules manage database connections and SQL operations. The data_pipeline module handles validation, duplicate removal, missing values, and outliers. The src/cache.py module uses FakeRedis to cache GET /movies responses for 90 seconds, reducing unnecessary database queries. The cache is cleared whenever movies are uploaded or processed to prevent outdated results. The /movies/search endpoint supports filtering by rating and selecting columns without caching.


How to run:

Install

pip install -r requirements.txt


Start the API:

python -m uvicorn main:app --reload

Access the API documentation at `http://127.0.0.1:8000/docs`.

Run tests:

python -m pytest tests -v

Example Processing Request

After uploading `fixtures/sample_movies.csv`, send a POST request to `/movies/process` with:

```json
{
  "validation": {
    "required_columns": ["title", "release_year", "rating", "genre"],
    "numeric_columns": ["release_year", "rating"]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {
      "enabled": true,
      "axis": "rows"
    },
    "outliers": {
      "enabled": true,
      "columns": ["rating"],
      "method": "iqr",
      "threshold": 1.5
    }
  }
}
```

### Expected Response

```json
{
  "validation_rows_removed": 0,
  "cleaning_report": {
    "rows_before": 20,
    "rows_after": 16,
    "rows_removed": 4,
    "columns_before": 4,
    "columns_after": 4,
    "columns_removed": 0
  }
}
```