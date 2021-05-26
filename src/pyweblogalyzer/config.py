import logging


class Config(object):
    """This is the basic configuration class for BorgWeb."""

    #
    # Logging settings
    #
    LOG_FILE = None  # "pyweblogalyzer.log"
    LOG_LEVEL = logging.INFO

    #
    #: Dashboard server settings
    #
    HOST = "0.0.0.0"  # use 0.0.0.0 to bind to all interfaces
    PORT = 9200  # ports < 1024 need root
    DEBUG = True  # if True, enable reloader and debugger

    #
    # Log collector settings
    #
    # Period in second to read new log data
    COLLECTION_DELAY_SECS = 60

    # Path to the access log file. If the path is a folder, all access.log files in the folder will be parsed
    WEB_LOG_PATH = "etc/dev/access.log"

    # Date and time parsing string. Reference:
    # https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes
    LOG_DATE_TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"

    # Enable ip geolocalisation
    ENABLE_GEOLOC = False

    # Log format. The following info are accepted, use {} to ignore
    # remote_ip:  Remote client IP
    # datetime:   Date and time in format LOG_DATE_TIME_FORMAT
    # request:    HTTP request
    # status:     HTTP status code
    # bytes_sent: Size of the request body sent in bytes
    # referer:    HTTP referer
    # hostname:   Server hostname from the request
    # user_agent: HTTP user agent
    # request_time: Request time in seconds (decimals for ms/ns precision)
    LOG__FORMAT = (
        '{remote_ip} - {} [{datetime}] "{request}" {status} {bytes_sent}'
        ' "{referer}" {hostname} "{user_agent}" "{request_time}" "{}"'
    )

    # List of client ips and requests to be excluded from the statistics
    EXCLUDE_REMOTE_IP = []
    EXCLUDE_REQUESTS = ["/metrics"]

    # List of local networks (cannot be geolocalised)
    LOCAL_NETWORKS=["192.168.0.0/24", "192.168.13.0/24"]

    # Root path of log enrichers. All custom classes must be in this folder (or subfolders)
    LOG_ENRICHERS_ROOT = "/Users/viv/dev/pyweblogalyzer/etc/dev/log_enrichers"
    # Custom log enrichers, defined by the location of the main python file, and the class name.
    # All enrichers must inherit LogEnrichers (see collector/log_enrichers.py for more details).
    # Each enricher will be called with every parsed log entry, and can add auxiliary informations to them
    LOG_ENRICHERS = [
        {
            'class_path': "dwarferie.py",
            'class_name': 'DwarferieEnricher',
            'config': {'kodi_url': '192.168.0.199', 'kodi_port': 8080}
        }
    ]

    #
    # Dashboards settings
    #

    # Preset refresh times in seconds
    REFRESH_TIMES = [30, 60, 300, 600]

    # Format of the datetime displayed in datatables (https://momentjs.com/docs/#/parsing/)
    DATATABLE_TIME_DISPLAY_FORMAT = 'YYYY/MM/DD HH:mm:ss'

    # Each dashboard is specifed as dictionnary with a name that must be unique, and contains the following fields:
    #
    # Column titles are listed in dataset/weblogdata.py, and custom fields added during enrichment
    # (prefixed with aux_) can also be used
    #
    # Mandatory fields:
    #     table_title:    Table title. For contextual menu, if "{}" is in the string, it will be replaced by
    #                     the selected row's filter column value.
    #     display_cols:   List of columns to display in the table. All columns are selected if empty or None.
    #     filter:         For contextual dashboard only, column to filter with the value passed when clicked.
    #                     Also used by the non contextual dashboad links to know which value to pass to the
    #                     contextual dashboard when a row is clicked.
    #                     Required for contextual dashboards.
    #
    # Optional fields:
    #     contextual:     If False, badge/table/graph are displayed as configured on the main dashboard.
    #                     If False, the graph and table are intended to be referred to by a dashboard, and
    #                     displayed using a specific filter based on the row clicked. Default to False
    #
    #     count_title:    Column title for the count of duplicates, if group_by_cols is specified. Default to "count"
    #     group_by_cols:  List of columns to group by unique values, removing duplicates and add a column with
    #                     the occurrences count of each value. No grouping or counting if empty or None
    #     time_title:     Column title for the count per time period, if time_group is specified. Default to "tcount"
    #     time_group:     Group by the specified time period. For format of the time period , see:
    #                     https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases
    #                     The 'timestamp' column is updated with the time period start of the row
    #                     Columns of each row in the period are summed up, non number columns are removed
    #                     Applied after the group_by_cols if specified, so the count_title column is available.
    #     graph_config:   Configuration of the  potly.js graph (https://plotly.com/javascript/)
    #                     In the data labels, put the column name containing the x and y axis data, and in each dataset
    #                     Column names for axis must be in the table (in display_cols or time_title or count_title)
    #
    # Optional fields, Non Contextual dashboards only:
    #     badge_title:    If not None, adds a badge widget with the specified title and table row count as value.
    #                     Unused for contextual dashboards.
    #                     count of occurences of each value.
    #     badge_type:     Determines the color band: black, gray (default), info, success, warning, failure
    #     on_click:       Name of the contextual dashboard to display when a row is clicked
    #                     Unused for contextual dashboards.
    #     large:          If True, the dashboard will take the whole width of the screen. Default is False
    DASHBOARDS_CONFIG = {
        "requests": {
            "table_title": "Requests",
            "time_title": "count",
            "time_group": "1h",
            "graph_config": {
                'data': [
                    {'title': 'requests', 'type': 'scatter', 'x': "timestamp", 'y': "count"},
                    {'title': 'byte sent', 'type': 'scatter', 'x': "timestamp", 'y': "bytes_sent", 'yaxis': 'y2'}
                ],
                'layout': {
                    'xaxis': {'type': 'date', 'tickformat': '%d/%m/%y %H:%M:%S'},
                    'yaxis': {'title': 'Requests'},
                    'yaxis2': {'title': 'bytes sent', 'overlaying': 'y', 'side': 'right'},
                },
            },
            "display_cols": ["timestamp", "bytes_sent"],
            "on_click": "ctxt_requests",
        },
        "codes": {
            "badge_title": None,
            "badge_type": "info",
            "table_title": "Requests per status code",
            "count_title": "count",
            "display_cols": ["request_status", "http_url"],
            "group_by_cols": ["request_status", "http_url"],
            "graph_config": {
                'data': [{'type': 'pie', 'labels': "request_status", 'values': "count"}],
                'layout': {
                    'xaxis': {},
                    'yaxis': {'title': 'Requests'},
                },
            },
            "on_click": "ctxt_codes",
        },
        "remote_ips": {
            "badge_title": "Total unique IPs",
            "table_title": "Unique IPs",
            "count_title": "IP count",
            "display_cols": ["remote_ip", "city", "country"],
            "group_by_cols": ['remote_ip'],
            "graph_config": {
                'data': [{'type': 'bar', 'x': "remote_ip", 'y': "IP count"}],
                'layout': {
                    'xaxis': {},
                    'yaxis': {'title': 'Requests'},
                },
            },
            "on_click": "ctxt_ips",
        },
        "countries": {
            "badge_title": "Total countries",
            "badge_type": "info",
            "table_title": "Requests per country",
            "count_title": "Requests count",
            "display_cols": ["country"],
            "group_by_cols": ['country'],
            "graph_config": {
                'data': [{'type': 'bar', 'x': "country", 'y': "Requests count"}],
                'layout': {
                    'xaxis': {},
                    'yaxis': {'title': 'Requests'},
                },
            },
            "on_click": "ctxt_countries",
        },
        "cities": {
            "badge_title": "Total cities",
            "badge_type": "info",
            "table_title": "Requests per city",
            "count_title": "Requests count",
            "display_cols": ["city", "country"],
            "group_by_cols": ['city'],
            "graph_config": {
                'data': [{'type': 'bar', 'x': "city", 'y': "Requests count"}],
                'layout': {
                    'xaxis': {},
                    'yaxis': {'title': 'Requests'},
                },
            },
            "on_click": "ctxt_cities",
        },
        "urls": {
            "badge_title": None,
            "table_title": "Unique URLs",
            "count_title": "URLs count",
            "display_cols": ["http_url"],
            "group_by_cols": ['http_url'],
            "graph_config": {
                'data': [{'type': 'bar', 'x': "http_url", 'y': "URLs count"}],
                'layout': {
                    'xaxis': {},
                    'yaxis': {'title': 'Requests'},
                },
            },
            "on_click": "ctxt_urls",
        },
        "browsers": {
            "badge_title": "Browsers",
            "badge_type": "info",
            "table_title": "Browsers",
            "count_title": "count",
            "display_cols": ["browser"],
            "group_by_cols": ['browser'],
            "graph_config": {
                'data': [{'type': 'pie', 'values': "count", 'labels': "browser"}],
                'layout': {
                    'xaxis': {},
                    'yaxis': {'title': 'Requests'},
                },
                'config': {
                    'scrollZoom': True,
                    'responsive': True,
                },
            },
            "on_click": "ctxt_browsers",
        },
        "os": {
            "badge_title": "OS",
            "badge_type": "info",
            "table_title": "OS",
            "count_title": "count",
            "display_cols": ["os"],
            "group_by_cols": ['os'],
            "graph_config": {
                'data': [{'type': 'pie', 'labels': "os", 'values': "count"}],
                'layout': {
                    'xaxis': {},
                    'yaxis': {'title': 'Requests'},
                },
                'config': {
                    'scrollZoom': True,
                    'responsive': True,
                },
            },
            "on_click": "ctxt_os",
        },
        "devices": {
            "badge_title": "Devices",
            "badge_type": "info",
            "table_title": "Devices",
            "count_title": "count",
            "display_cols": ["device"],
            "group_by_cols": ['device'],
            "graph_config": {
                'data': [{'type': 'pie', 'labels': "device", 'values': "count"}],
                'layout': {
                    'xaxis': {},
                    'yaxis': {'title': 'Requests'},
                },
                'config': {
                    'scrollZoom': True,
                    'responsive': True,
                },
            },
            "on_click": "ctxt_devices",
        },
        "downloads": {
            "badge_title": "Total Downloads",
            "badge_type": "info",
            "table_title": "Downloads",
            "count_title": None,
            "display_cols": [
                "aux_kodi_type", "aux_kodi_item", "remote_ip", "city", "country", "bytes_sent", "request_time", "timestamp"
            ],
            "group_by_cols": None,
            "on_click": "ctxt_downloads",
        },
        "logs": {
            "badge_title": "Total requests",
            "table_title": "Logs",
            "count_title": None,
            "large": True,
            "display_cols": [
                "timestamp",
                "remote_ip",
                "http_operation",
                "http_url",
                "request_status",
                "city", "country",
                "bytes_sent"
            ],
            "group_by_cols": None,
            "on_click": "ctxt_logs",
        },

        # Contextual dashboards
        "ctxt_ips": {"contextual": True, "table_title": "Requests details for ip {}", "filter": "remote_ip"},
        "ctxt_requests": {"contextual": True, "table_title": "Requests details from time {}", "filter": "timestamp"},
        "ctxt_codes": {"contextual": True, "table_title": "Details for http status {}", "filter": "request_status"},
        "ctxt_countries": {"contextual": True, "table_title": "Requests from {}", "filter": "country"},
        "ctxt_cities": {"contextual": True, "table_title": "Requests from {}", "filter": "city"},
        "ctxt_urls": {"contextual": True, "table_title": "Requests for {}", "filter": "http_url"},
        "ctxt_browsers": {"contextual": True, "table_title": "Requests from browser {}", "filter": "browser"},
        "ctxt_devices": {"contextual": True, "table_title": "Requests from device {}", "filter": "device"},
        "ctxt_os": {"contextual": True, "table_title": "Requests from OS {}", "filter": "os"},
        "ctxt_logs": {"contextual": True, "table_title": "Logs at {}", "filter": "timestamp"},
        "ctxt_downloads":
        {
            "contextual": True,
            "table_title": "Downloads from {}",
            "filter": "aux_kodi_type",
            "group_by_cols": ["remote_ip"],
            "display_cols": [
                "aux_kodi_item",
                "remote_ip", "city",
                "country",
                "bytes_sent",
                "request_time",
                "timestamp",
                "request_status"
            ]
        },
    }
