from pathlib import Path

import pandas as pd
import pytest

from src import MovieStorage
import main


def get_ids(records):
    """Return the "id" value of every record, in order."""
    ids = []
    for record in records:
        ids.append(record["id"])
    return ids


def get_titles(records):
    """Return the "title" value of every record, in order."""
    titles = []
    for record in records:
        titles.append(record["title"])
    return titles




def test_movies_persist(client, test_storage, uploaded_movies):
    restarted_storage = MovieStorage(test_storage.db_path)

    movies = restarted_storage.get()
    movie_count = restarted_storage.count_movies()

    original_titles = pd.read_csv(Path("fixtures") / "sample_movies.csv")["title"]
    assert movie_count == 20
    assert len(movies) == 20
    assert list(movies.columns) == ["title", "release_year", "rating", "genre"]
    assert list(movies["title"]) == list(original_titles)

    stored_records = restarted_storage.select_columns(["title"], limit=100)
    response = client.get("/movies", params={"limit": 100})
    assert response.status_code == 200

    expected_ids = list(range(1, 21))
    assert get_ids(stored_records) == expected_ids
    assert get_ids(response.json()["data"]) == expected_ids


def test_cache_and_processing(client, uploaded_movies, processing_body):
    response_100 = client.get("/movies", params={"limit": 100})
    response_1 = client.get("/movies", params={"limit": 1})

    assert response_100.status_code == 200
    assert response_1.status_code == 200
    assert main.cache.get(100) == response_100.json()
    assert main.cache.get(1) == response_1.json()

    repeated_response = client.get("/movies", params={"limit": 100})
    assert repeated_response.status_code == 200
    assert repeated_response.json() == response_100.json()

    process_response = client.post("/movies/process", json=processing_body)
    assert process_response.status_code == 200

    report = process_response.json()
    assert report["validation_rows_removed"] == 0
    assert report["cleaning_report"] == {
        "rows_before": 20,
        "rows_after": 16,
        "rows_removed": 4,
        "columns_before": 4,
        "columns_after": 4,
        "columns_removed": 0,
    }

    assert main.cache.get(100) is None
    assert main.cache.get(1) is None

    new_response = client.get("/movies", params={"limit": 100})
    assert new_response.status_code == 200

    new_body = new_response.json()
    expected_titles = []
    for letter in "ABCDEFGHIJKLMNOP":
        expected_titles.append(f"Movie {letter}")
    assert new_body["total_rows"] == 16
    assert get_titles(new_body["data"]) == expected_titles

    assert get_ids(new_body["data"]) == list(range(1, 17))

    assert main.cache.get(100) == new_body


def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    first_response = client.get("/movies", params={"limit": 100})
    assert first_response.status_code == 200

    
    def fail_if_called(*args, **kwargs):
        pytest.fail("The database was used even though the response was cached")

    monkeypatch.setattr(main.storage, "select_columns", fail_if_called)
    monkeypatch.setattr(main.storage, "count_movies", fail_if_called)

    second_response = client.get("/movies", params={"limit": 100})
    assert second_response.status_code == 200
    assert second_response.json() == first_response.json()

def test_upload_csv(client, sample_csv_bytes):
    response = client.post(
        "/upload",
        files={"file": ("sample_movies.csv", sample_csv_bytes, "text/csv")},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "filename": "sample_movies.csv",
        "rows": 20,
        "columns": 4,
        "column_names": ["title", "release_year", "rating", "genre"],
    }


def test_upload_reorders_columns(client):
    contents = b"genre,rating,title,release_year\nDrama,7.5,Movie Z,2001\n"
    response = client.post("/upload", files={"file": ("movies.csv", contents)})

    assert response.status_code == 200, response.text
    assert response.json()["column_names"] == ["title", "release_year", "rating", "genre"]
    assert client.get("/movies").json()["data"] == [
        {"id": 1, "title": "Movie Z", "release_year": 2001, "rating": 7.5, "genre": "Drama"}
    ]


@pytest.mark.parametrize(("filename", "contents"), [
    ("movies.txt", b"data"),
    ("movies.csv", b""),
    ("movies.csv", b"title,rating\nMovie A,8.0\n"),
    ("movies.csv", b"title,release_year,rating,genre,extra\nMovie A,2020,8.0,Drama,x\n"),
    ("movies.csv", b"title,release_year,rating,genre\n"),
])
def test_upload_rejects_bad_files(client, filename, contents):
    response = client.post("/upload", files={"file": (filename, contents)})

    assert response.status_code == 400, response.text
    assert client.get("/health").status_code == 200


def test_get_movies(client, uploaded_movies):
    response = client.get("/movies", params={"limit": 2})

    assert response.status_code == 200, response.text
    assert response.json() == {
        "data": [
            {"id": 1, "title": "Movie A", "release_year": 2020, "rating": 8.0, "genre": "Drama"},
            {"id": 2, "title": "Movie B", "release_year": 2021, "rating": 8.5, "genre": "Comedy"},
        ],
        "total_rows": 20,
    }


def test_get_movies_when_empty(client):
    response = client.get("/movies")

    assert response.status_code == 200, response.text
    assert response.json() == {"data": [], "total_rows": 0}


def test_search_default_columns(client, uploaded_movies):
    response = client.get("/movies/search", params={"min_rating": 8.5, "limit": 2})

    assert response.status_code == 200, response.text
    assert response.json() == [
        {"id": 4, "title": "Movie C"},
        {"id": 2, "title": "Movie B"},
    ]

def test_search_selected_columns(client, uploaded_movies):
    response = client.get(
        "/movies/search",
        params={"columns": ["title", "rating"], "min_rating": 8.5, "limit": 2},
    )

    assert response.status_code == 200, response.text
    assert response.json() == [
        {"id": 4, "title": "Movie C", "rating": 9.0},
        {"id": 2, "title": "Movie B", "rating": 8.5},
    ]

def test_search_no_matches(client, uploaded_movies):
    response = client.get("/movies/search", params={"min_rating": 10})

    assert response.status_code == 200, response.text
    assert response.json() == []

def test_search_unsupported_column(client, uploaded_movies):
    response = client.get("/movies/search", params={"columns": ["id; DROP TABLE movies"]})

    assert response.status_code == 400, response.text
    assert client.get("/movies").json()["total_rows"] == 20

def test_upload_replaces_collection_and_clears_cache(client, sample_csv_bytes, uploaded_movies):
    client.get("/movies", params={"limit": 100})
    assert main.cache.get(100) is not None

    response = client.post(
        "/upload",
        files={"file": ("sample_movies.csv", sample_csv_bytes, "text/csv")},
    )

    assert response.status_code == 200, response.text
    assert main.cache.get(100) is None
    assert client.get("/movies").json()["total_rows"] == 20


def test_process_without_movies(client, processing_body):
    response = client.post("/movies/process", json=processing_body)

    assert response.status_code == 400, response.text


def test_failed_processing_preserves_database_and_cache(client, test_storage, uploaded_movies):
    cached_response = client.get("/movies", params={"limit": 100}).json()
    movies_before = test_storage.get()

    response = client.post(
        "/movies/process",
        json={"validation": {"numeric_columns": ["missing"]}},
    )

    assert response.status_code == 400, response.text
    assert test_storage.get().equals(movies_before)
    assert main.cache.get(100) == cached_response
