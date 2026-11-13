import logging
import sqlite3

import pandas as pd

from .database import get_connection, initialize_database

logger = logging.getLogger(__name__)
MOVIE_COLUMNS = ["title", "release_year", "rating", "genre"]


class MovieStorage:
    def __init__(self, db_path="data/movies.db"):
        self.db_path = db_path
        initialize_database(self.db_path)
    
    def save(self, df):
        df = df.reindex(columns=MOVIE_COLUMNS).astype(object)
        rows = []
        for row in df.itertuples(index=False, name=None):
            clean_row = []
            for value in row:
                if pd.isna(value):
                    clean_row.append(None)
                else:
                    clean_row.append(value)
            rows.append(tuple(clean_row))

        connection = get_connection(self.db_path)
        try:
            connection.execute("DELETE from movies")
            sql_statement = "INSERT INTO movies (title, release_year, rating, genre) VALUES (?, ?, ?, ?)"
            connection.executemany(sql_statement, rows)
            connection.commit()
        except sqlite3.Error:
            connection.rollback()
            logger.error(f"Cannot save movies to database")
        finally:
            connection.close()


    def get(self):
        """Return the four movie columns as a DataFrame, ordered by id."""
        connection = get_connection(self.db_path)
        try:
            sql_statement = "SELECT title, release_year, rating, genre FROM movies ORDER BY id"
            rows = connection.execute(sql_statement).fetchall()
            data = []
            for row in rows:
                data.append(tuple(row))
            df = pd.DataFrame(data, columns=MOVIE_COLUMNS)
            logger.debug(f"Retrieved movies from SQLite: rows={len(df)}")
            return df
        except sqlite3.Error:
            logger.error(f"Error doing the query: " + sql_statement) 
        finally:
            connection.close()

    def select_columns(self, columns, limit=5):
        """Return id plus the requested movie columns, ordered by id."""
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")

        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            sql_statement = f"SELECT {selected_columns} FROM movies ORDER BY id LIMIT ?"
            rows = connection.execute(sql_statement, (limit,)).fetchall()
            records = []
            for row in rows:
                records.append(dict(row))
            return records

        finally:
            connection.close()

    def count_movies(self):
        """Return the number of stored movies using SQL COUNT(*)."""
        connection = get_connection(self.db_path)
        try: 
            sql_statement = "SELECT COUNT(*) from movies"
            count = connection.execute(sql_statement).fetchone()[0]
            return count
        finally:
            connection.close()

    def query_movies(self, columns, min_rating, limit):
        """Return selected fields from matching movies using SQL."""
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")

        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")
        
        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            sql_statement = f"SELECT {selected_columns} FROM movies WHERE rating > {min_rating} ORDER BY rating DESC, id LIMIT {limit}"
            rows = connection.execute(sql_statement).fetchall()
            records = []
            for row in rows:
                records.append(dict(row))
            logger.debug(f"Selected columns: {selected_columns} Row count: {len(rows)}")
            return records
        finally:
            connection.close()