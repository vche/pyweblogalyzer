from pandas import DataFrame, DatetimeIndex


class WebLogDataSet:
    def __init__(self):
        self._fields = []
        self._data = []
        self._index = []

    def add(self, log_data):
        fields, values = log_data.to_arrays()
        self._data.append(values)
        self._index.append(log_data.timestamp)

        # Only store the fields of the first log. All other logs are required to have the same ones.
        if not self._fields:
            self._fields = fields

    def get_dataframe(self):
        # Creating a new dataframe reordered by date from the dict is the most efficient way,
        # as updating a df makes panda copying large chunks of data
        return DataFrame(self._data, columns=self._fields, index=DatetimeIndex(self._index)).sort_index()
