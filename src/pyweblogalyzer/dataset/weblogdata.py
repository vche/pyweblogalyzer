import pandas

# Required info fields. Accessible directly as attributes, always created at init.
LOG_INFOS = [
    "remote_ip",
    "http_referer",
    "hostname",
    "timestamp",
    "bytes_sent",
    "request_time",
    "request_status",
    "city",
    "country",
    "lat",
    "long",
    "http_operation",
    "http_url",
    "protocol",
    "browser",
    "os",
    "device",
]

LOG_AUX_INFO_PREFIX = "aux_"


class WebLogData:
    """Log data."""
    DASHBOARD_TIMESTAMP_EXPORT_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

    def __init__(self, **kwargs):
        """Initialize log data."""
        self._data = {}
        # Initialize all reauired attributes, using args when specified
        for field in LOG_INFOS:
            # For timestamps, keep the object, but put the string version in the dict to export to as as
            # serializable datatable. That sucks but datetime are converted to pandas Timestamp, not serializable
            if field == "timestamp" and kwargs.get(field, None):
                self.timestamp = kwargs[field]
                self._data[field] = self.timestamp.strftime(self.DASHBOARD_TIMESTAMP_EXPORT_FORMAT)
            else:
                self._data[field] = kwargs.get(field, None)
            # self._data[field] = kwargs.get(field, None)

    def __getattr__(self, name):
        # When an attribute is not found try to get it from the log data
        if name in self._data:
            return self._data[name]
        raise AttributeError(name)

    def __str__(self):
        return str(self._data)

    def add_aux_info(self, name, value):
        """Add auxiliary (optional) info to the log data. Prefixed with 'aux_'. to be used by enrichers."""
        self._data[LOG_AUX_INFO_PREFIX + name] = value

    def to_arrays(self):
        return list(self._data.keys()), list(self._data.values())
