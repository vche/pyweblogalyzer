import logging
from pandas import DataFrame, DatetimeIndex
from pyweblogalyzer.dataset.weblogdata import WebLogData
from threading import Lock
from datetime import timezone
import pandas

class WebLogDataSet:
    # Max waait time for getting a lock is 60s
    LOCK_TIMEOUT = 60.0

    def __init__(self):
        self._fields = []
        self._data = []
        self._index = []
        self._dataset_lock = Lock()
        self.log = logging.getLogger(__name__)
        self._empty_df = self._build_empty_dataset()

    def _build_empty_dataset(self):
        elt = WebLogData()
        fields, values = elt.to_arrays()
        return DataFrame([values], columns=fields, index=DatetimeIndex([elt.timestamp]))

    def add(self, log_data):
        fields, values = log_data.to_arrays()
        self._data.append(values)
        self._index.append(log_data.timestamp)

        # Only store the fields of the first log. All other logs are required to have the same ones.
        if not self._fields:
            self._fields = fields

    def get_dataframe(self):
        if self.lock():
            # Creating a new dataframe reordered by date from the dict is the most efficient way,
            # as updating a df makes panda copying large chunks of data
            try:
                # df = DataFrame(self._data, columns=self._fields, index=DatetimeIndex(self._index, dtype='datetime64[ns, Europe/London]')).sort_index()
                df = DataFrame(self._data, columns=self._fields, index=DatetimeIndex(pandas.to_datetime(self._index, utc=True))).sort_index()
                # return DataFrame([values], columns=fields, index=DatetimeIndex()
            except Exception as e:
                self.log.exception(f"Error getting dataframe: {e}")
                df = self._empty_df
            self.unlock()
        else:
            df = self._empty_df
        return df

    def lock(self):
        res = self._dataset_lock.acquire(timeout=self.LOCK_TIMEOUT)
        if not res:
            self.log.error("Couldn't acquire lock on dataset after %s seconds", self.LOCK_TIMEOUT)
        return res

    def unlock(self):
        try:
            self._dataset_lock.release()
        except RuntimeError as e:
            self.log.error("Trying to release an unlocked lock %s", e)
