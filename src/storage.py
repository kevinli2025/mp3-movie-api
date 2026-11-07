import logging

logger = logging.getLogger(__name__)


class DatasetStorage:
    def __init__(self):
        self._store = {}
        self._counter = 0

    def save(self, df, filename):
        self._counter += 1
        dataset_id = self._counter
        self._store[dataset_id] = {
            "filename" : filename,
            "data" : df.copy()
        }

        logger.debug(f"Stored dataset: id={dataset_id} rows={len(df)}")
        return dataset_id

    def get(self, dataset_id):
        if dataset_id not in self._store:
            return None

        df = self._store[dataset_id]["data"]
        logger.debug(f"Retrieved dataset copy: id={dataset_id} rows={len(df)}")
        return df.copy()
            
    def get_metadata(self, dataset_id):
        if dataset_id not in self._store:
            return None
        
        df = self._store[dataset_id]["data"]

        metadata = {
            "id": dataset_id,
            "filename": self._store[dataset_id]["filename"],
            "rows": df.shape[0],
            "columns": df.shape[1],
            "column_names": df.columns.tolist()
        }

        logger.debug(f"Retrieved metadata: id={dataset_id}")
        return metadata


    def update(self, dataset_id, df):
        if dataset_id not in self._store:
            return False
        
        self._store[dataset_id]["data"] = df.copy()
        logger.debug(f"Updated dataset: id={dataset_id}, rows={len(df)}")
        return True
       
       
    def clear(self):
        """Clear all data and reset the ID counter."""
        self._store.clear()
        self._counter = 0
