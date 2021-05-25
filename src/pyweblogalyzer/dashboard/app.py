import os
import time
import urllib.parse
import json
import pandas
import numpy

from copy import deepcopy
from flask import Blueprint, Flask, current_app, render_template, url_for
from pyweblogalyzer.dataset.weblogdata import WebLogData

appblueprint = Blueprint("dashboard", __name__)


def hex_color_to_rgba(hex_color, opacity):
    """Convert a color code string like '#123' or '#123456' to an rgba with opacity like 'rgba(12,34},56},0.2})'"""
    hex = hex_color.replace('#', '')

    if len(hex) == 3:
        hex = f"${hex[0]}${hex[0]}${hex[1]}${hex[1]}${hex[2]}${hex[2]}"

    r = int(hex[0:2], 16)
    g = int(hex[2:4], 16)
    b = int(hex[4:6], 16)
    return f"rgba({r},{g},{b},{opacity / 100})"


class DashboardApp(Flask):
    CONFIG_KEY_DASHBOARDS = "DASHBOARDS_CONFIG"
    CONFIG_KEY_BADGE_TITLE = "badge_title"
    CONFIG_KEY_BADGE_TYPE = "badge_type"
    CONFIG_KEY_TABLE_TITLE = "table_title"
    CONFIG_KEY_COUNT_TITLE = "count_title"
    CONFIG_KEY_DISPLAY_COLS = "display_cols"
    CONFIG_KEY_GROUP_BY_COLS = "group_by_cols"
    CONFIG_KEY_CONTEXTUAL = "contextual"
    CONFIG_KEY_FILTER = "filter"
    CONFIG_KEY_ONCLICK = "on_click"
    CONFIG_KEY_LARGE = "large"
    CONFIG_KEY_TIME_GROUP = "time_group"
    CONFIG_KEY_TIME_TITLE = "time_title"
    CONFIG_KEY_GRAPH = "graph_config"
    DEFAULT_BADGE_TYPE = "gray"

    def __init__(self, dataset, config_class, config_env: None):
        super().__init__(__name__)
        self._dataset = dataset

        self.config.from_object(config_class)
        if config_env and os.environ.get(config_env):
            self.config.from_envvar(config_env)

        self.register_blueprint(appblueprint)

    def run(self):
        """Start the web app."""
        # Don't use the reloader as it restarts the app dynamically, creating a new collector
        super().run(host=self.config["HOST"], port=self.config["PORT"], debug=self.config["DEBUG"], use_reloader=False)
        self.logger.info("Dashboard started")

    def get_dashboard_table_data(
        self,
        logdata,
        display_cols,
        groupby_cols=None,
        count_title=None,
        filter=None,
        value=None,
        time_group=None,
        time_title=None
    ):
        """Compute the data table for this dashboard."""
        tabledata = logdata

        # Filter rows based on the value if specified
        if filter and value:
            # Convert the value to int or float if it represents a number
            if value.isdigit():
                value = int(value)
            else:
                try:
                    value = float(value)
                except ValueError:
                    pass
            tabledata = tabledata[tabledata[filter] == value]

        # Filter out to keep specify columns
        if display_cols:
            tabledata = tabledata[display_cols].dropna()

        # If grouping specified, add a column with the duplicates count
        if groupby_cols:
            tabledata[count_title] = tabledata.groupby(groupby_cols)[groupby_cols[0]].transform('size')
            tabledata = tabledata.drop_duplicates(subset=groupby_cols)
            # Not really necessary as js will reorder re_index()
            tabledata.sort_values(by=count_title , axis=0, inplace=True, ignore_index=True, ascending=False)

        # If time grouping is specified
        if time_group:
            # Create a column with a unit to be summed up by period, and set the ts col to 1 to avoid it being removed
            tabledata[time_title] = 1
            tabledata['timestamp'] = 1
            tabledata = tabledata.groupby(pandas.Grouper(freq=time_group)).sum()
            # Update the timestamp column with a string version of the period time
            tabledata['timestamp'] = tabledata.index.strftime(WebLogData.DASHBOARD_TIMESTAMP_EXPORT_FORMAT)
            # tabledata['timestamp'] = tabledata.index.astype(numpy.int64) // 10 ** 6

        # print(f"pipo {tabledata}")
        return tabledata

    def _update_render_config(self, graph_config):
        """Update the chart.js graph config to fill missing fields and replace labels and datasets.
        If the config is not valid; the graph will be ignored
        """
        # DEFAULT_GRAPH_COLORS = [
        #     "#3e95cd", "#8e5ea2", "#3cba9f", "#e8c3b9", "#c45850",
        #     "#F92672", "#FD971F", "#E69F66", "#E6DB74", "#A6E22E",
        #     "#66D9EF", "#AE81FF", "#272822", "#F8F8F2", "#75715E",
        # ]
        # DEFAULT_GRAPH_BG_COLORS = [hex_color_to_rgba(color, 40) for color in DEFAULT_GRAPH_COLORS]
        DEFAULT_OPTIONS = {
            'data': {
                'fill': 'tozeroy',
                'line': {
                    'shape': 'spline',
                },
            },
            'layout': {
                'height': 250,
                'automargin': True,
                'autosize': True,
                'margin': {'l': 60, 'r': 20, 't': 30, 'b': 65, 'pad': 4},
                'plot_bgcolor': '#F5F5F5',
                'paper_bgcolor': "rgba(0,0,0,0)",
            },
            'config': {
                'scrollZoom': True,
                'responsive': True,
            },
        }

        # Make sure to render a copy and not update the config
        rendered_config = deepcopy(graph_config)

        # Check required info are present
        for field in ['data', 'layout']:
            if field not in rendered_config:
                self.logger.warning(f"Graph config missing required field {field}, graph ignored({rendered_config})")
                return None

        # Fill missing config with defaults
        if 'config' not in rendered_config:
            rendered_config['config'] = DEFAULT_OPTIONS['config']
        else:
            for key in DEFAULT_OPTIONS['layout']:
                rendered_config['layout'].setdefault(key, DEFAULT_OPTIONS['layout'][key])

        # Fill default layout
        for key in DEFAULT_OPTIONS['layout']:
            rendered_config['layout'].setdefault(key, DEFAULT_OPTIONS['layout'][key])

        # Fill default dataset options and set empty label and data list
        for dataset in rendered_config['data']:
            for key in DEFAULT_OPTIONS['data']:
                for dataset in rendered_config['data']:
                    dataset.setdefault(key, DEFAULT_OPTIONS['data'][key])
            for axis_key in self._get_dataset_axis_labels(dataset):
                rendered_config[axis_key] = []

        return rendered_config

    def _get_dataset_axis_labels(self, dataset_config):
        """Returns the key couple present in the dict."""
        key_sets = [["x", "y"], ["values", "labels"]]
        for keyset in key_sets:
            if all(key in dataset_config for key in keyset):
                return keyset
        self.logger.error(f"No key found for graph axis data in {dataset_config.keys()}")
        return []

    def _get_graph_dataset_columns(self, graph_config):
        """Extract the xaxis column name, and the list of yaxis columnn names."""
        try:
            xaxis = []
            yaxis = []
            for dataset in graph_config['data']['data']:
                xaxis.append(graph_config['data']['labels'])
            yaxis = [dataset['data'] for dataset in graph_config['data']['datasets']]
            return xaxis, yaxis
        except KeyError as e:
            self.log.warning(f"Missing key {e} in graph config, ignoring graph data")
        return None, None

    def _get_badge_id(self, dashboard_id):
        """Build a badge id for this dashboard's badge."""
        return f"{dashboard_id}_badge"

    def get_dashboard(self):
        """Build the html dashboard page with no data."""
        badges = {}
        dashboards = {}
        for db_id, db in self.config[self.CONFIG_KEY_DASHBOARDS].items():
            if not db.get(self.CONFIG_KEY_CONTEXTUAL, False):
                if db.get(self.CONFIG_KEY_BADGE_TITLE):
                    badges[self._get_badge_id(db_id)] = {
                        "title": db[self.CONFIG_KEY_BADGE_TITLE],
                        "type": db.get(self.CONFIG_KEY_BADGE_TYPE, self.DEFAULT_BADGE_TYPE),
                    }
                cols = deepcopy(db[self.CONFIG_KEY_DISPLAY_COLS])
                if db.get(self.CONFIG_KEY_COUNT_TITLE):
                    cols.append(db[self.CONFIG_KEY_COUNT_TITLE])
                if db.get(self.CONFIG_KEY_TIME_TITLE):
                    cols.append(db[self.CONFIG_KEY_TIME_TITLE])

                # If this db is large, but not at the beginning of a row, add an empty db
                if db.get(self.CONFIG_KEY_LARGE) and len(dashboards) % 2 != 0:
                    dashboards["_empty_"] = {"title": ""}

                dashboards[db_id] = {
                    "title": db[self.CONFIG_KEY_TABLE_TITLE],
                    "columns": cols,
                }
                # Add graph data if specified
                graph_config = db.get(self.CONFIG_KEY_GRAPH)
                if graph_config:
                    dashboards[db_id]["graph_config"] = self._update_render_config(graph_config)

                # If this db is large, add an invisible db to take the next slot
                if db.get(self.CONFIG_KEY_LARGE):
                    dashboards[db_id]["large"] = True
                    dashboards["_hidden_"] = {"title": ""}

        return render_template('index.html', badges=badges, dashboards=dashboards, config=self.config)

    def get_dashboard_data(self):
        """Get dashboard data to fill the html page."""
        a = time.time()
        # TODO: Update config to add data sent dashboard, missing graphs, missing context dbs
        # TODO: Add expand modebar button to open the graph in a modal window
        # TODO: Add auto reload
        # TODO: Update collector to scan all log files in a folder

        # Get the latest data
        logdata = self._dataset.get_dataframe()

        # Build a widget for each dashboard in the config
        display_data = []
        for dashboard_id, dashboard in self.config[self.CONFIG_KEY_DASHBOARDS].items():
            if not dashboard.get(self.CONFIG_KEY_CONTEXTUAL, False):
                db_data = {}
                tabledata = self.get_dashboard_table_data(
                    logdata,
                    display_cols=dashboard[self.CONFIG_KEY_DISPLAY_COLS],
                    groupby_cols=dashboard.get(self.CONFIG_KEY_GROUP_BY_COLS),
                    count_title=dashboard.get(self.CONFIG_KEY_COUNT_TITLE, "count"),
                    time_group=dashboard.get(self.CONFIG_KEY_TIME_GROUP),
                    time_title=dashboard.get(self.CONFIG_KEY_TIME_TITLE, "tcount"),
                )

                # If this db has a badge
                if dashboard.get(self.CONFIG_KEY_BADGE_TITLE):
                    db_data["badge_id"] = self._get_badge_id(dashboard_id)
                    db_data["badge_value"] = len(tabledata)

                # Dashboard table data
                db_data["db_id"] = dashboard_id
                db_data["table_data"] = tabledata.values.tolist()

                graph_config = dashboard.get(self.CONFIG_KEY_GRAPH)
                if graph_config and 'layout' in graph_config:
                    graph_data = {}
                    for dataset in graph_config['data']:
                        for key in self._get_dataset_axis_labels(dataset):
                            graph_data.setdefault(key, [])
                            graph_data[key].append(tabledata[dataset[key]].tolist())
                    db_data["graph_data"] = graph_data

                # If a context dashboard is specified, generate an example link
                # ctxt_db = dashboard.get(self.CONFIG_KEY_ONCLICK)
                # if ctxt_db:
                #     filter = self.config[self.CONFIG_KEY_DASHBOARDS][ctxt_db][self.CONFIG_KEY_FILTER]
                #     try:
                #         value = urllib.parse.quote(tabledata[filter][1], safe="")
                #         db_data["ctxt_link"] = url_for('dashboard.get_context_data', dashboard=dashboard_id, key=value)
                #     except KeyError:
                #         self.logger.warning(f"DB {dashboard_id}: No filtered data found for filter {filter}")

                display_data.append(db_data)

        page_data = {
            "dashboards": display_data,
            "start_date": str(logdata["timestamp"][0]),
            "end_date": str(logdata["timestamp"][len(logdata) - 1]),
        }

        b = time.time()
        print(f"exec: {b-a}")
        return page_data

    def context_data(self, dashboard, key):
        db = urllib.parse.unquote(dashboard)
        parent_dashboard_config = self.config[self.CONFIG_KEY_DASHBOARDS].get(db)
        ctxt_db = parent_dashboard_config.get(self.CONFIG_KEY_ONCLICK)
        # Only proceed further if a contextual dashboard is configured
        if ctxt_db:
            dashboard_config = self.config[self.CONFIG_KEY_DASHBOARDS].get(ctxt_db)
            if dashboard_config:
                logdata = self._dataset.get_dataframe()
                tabledata = self.get_dashboard_table_data(
                    logdata,
                    display_cols=dashboard_config[self.CONFIG_KEY_DISPLAY_COLS],
                    groupby_cols=dashboard_config.get(self.CONFIG_KEY_GROUP_BY_COLS),
                    count_title=dashboard_config.get(self.CONFIG_KEY_COUNT_TITLE, "count"),
                    filter=dashboard_config.get(self.CONFIG_KEY_FILTER),
                    value=urllib.parse.unquote(key)
                )
                # return tabledata.to_html()
                title = dashboard_config["table_title"].format(key)
                modal_data = {}
                modal_data["table_id"] = "db-modal-table"
                modal_data["table_cols"] = tabledata.columns.tolist()
                modal_data["table_data"] = tabledata.values.tolist()
                modal_data["html"] = render_template('modal.html', modal_data=modal_data, table_title=title)
                return modal_data
            else:
                self.log.warning(f"No dashboard {dashboard}, check the configuration")
        return ""


@appblueprint.route("/", methods=["GET"])
def get_index():
    return current_app.get_dashboard()


@appblueprint.route("/data", methods=["GET"])
def get_data():
    return current_app.get_dashboard_data()


@appblueprint.route("/context/<string:dashboard>/<string:key>", methods=["GET"])
def get_context_data(dashboard, key):
    return current_app.context_data(dashboard, key)