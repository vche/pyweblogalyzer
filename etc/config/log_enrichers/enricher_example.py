from pyweblogalyzer import LogEnricherPlugin, install_and_import

# As this is dynamycally run from pywebalyzer, standard pip install and import won't work,
# especially from docker or virtual env. To import external plugin, use this helper that will dynamically install
# the packages if needed, and import them
install_and_import(["requests", "beekeeper"])

# Import another module in the same folder or subfolders  is as usual.
# e.g. a class OtherClass from a file example2.py in the same folder:
# from example2 import OtherClass

from beekeeper import exceptions


class ExampleEnricher(LogEnricherPlugin):
    _tvshow_properties = ['episode', 'season', 'showtitle']
    _movies_properties = ['originaltitle', 'year']

    ENRICHED_KODI_TYPE = "kodi_type"
    ENRICHED_KODI_ITEM = "kodi_item"

    def __init__(self, config):
        # Always call the parent class init
        super().__init__(config)

        # The config passed is specified in the main config file alonf with the enricher class
        self._enable = self._config["enable_example"],

    def enrich_log(self, log_data):
        # This method is called for every new log collected, after parsing

        if self._enable:
            # Logdata is the parsed log, containing all fields listed in dataset.weblogdata.LOG_INFOS
            # All those information can be used and accessed as fields, e.g. log_data.http_url.
            # They are not meant to be altered.
            # But if needed, they must be uddated through the internal dict: log_data._data['http_url'] = "xxx"
            url_params = log_data.http_url.split('?')

            # A logger is provided
            self.log.debug("Parsed url %s", log_data.http_url)

            # Any new field can be added to the logs. they will be automatically prefixed with "aux_".
            # In this example, a new data column "aux_param" will be created and can be used in dashboards
            log_data.add_aux_info("param", url_params[1] if len(url_params) > 0 else None)
