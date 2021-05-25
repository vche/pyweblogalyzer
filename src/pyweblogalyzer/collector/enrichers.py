import importlib.util
import logging
import sys
from abc import ABC, abstractmethod
import subprocess


def install(package):
    "Install a package using pip."
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


def install_and_import(pkg_required):
    """Try to loads the specified packages, and try to install those who fails."""
    try:
        for pkg in pkg_required:
            __import__(pkg)
    except ModuleNotFoundError as e:
        print(f"Package not found, installing dependencies: {e}")
        for pkg in pkg_required:
            install(pkg)
            __import__(pkg)


class LogEnricherPlugin(ABC):
    """Base class for custom log enrichers.

    All enrichers must be placed in the configured folder LOG_ENRICHERS_ROOT (or a subfolder).
    Each enricher, must be declared in LOG_ENRICHERS in order to be ran
    To use external packages, 'install_and_import' must be call before the import with the list of dependencies.
    Each will be checked and installed if needed.
    The LOG_ENRICHERS_ROOT module is imported, so all enriched can import local packages in this folder,
    e.g. from some_module import SomeClass, where SomeClass is declared in LOG_ENRICHERS_ROOT/some_module.py
    The enrich_log() method is called with every parsed log entry, and the add_aux_info() method can be used
    to add any additional info to be used in dashboards. Those fields will always be prefixed with "aux_".
    Note that ALL logs must be added a value for the additional fields (can be None), not just some.
    """

    def __init__(self, config):
        self.log = logging.getLogger(__name__)
        self._config = config

    @abstractmethod
    def enrich_log(self, log_data):
        pass


class LogEnrichers:
    CONFIG_KEY_ENRICHERS_ROOT = "LOG_ENRICHERS_ROOT"
    CONFIG_KEY_ENRICHERS = "LOG_ENRICHERS"
    CONFIG_KEY_CLASS_PATH = "class_path"
    CONFIG_KEY_CLASS_NAME = "class_name"
    CONFIG_KEY_CONFIG = "config"

    def __init__(self, config):
        self._config = config
        self._enrichers = self._load_enrichers()
        self.log = logging.getLogger(__name__)

    def _load_enrichers(self):
        # Make sure the enricher can import modules from the enricher folder
        sys.path.append(self._config[self.CONFIG_KEY_ENRICHERS_ROOT])

        # Instantiate all declared enrichers
        enrichers = []
        for enricher_config in self._config[self.CONFIG_KEY_ENRICHERS]:
            class_path = "/".join(
                [self._config[self.CONFIG_KEY_ENRICHERS_ROOT], enricher_config[self.CONFIG_KEY_CLASS_PATH]]
            )
            try:
                enrichers.append(self._load__and_create_enricher(
                    class_path, enricher_config[self.CONFIG_KEY_CLASS_NAME], enricher_config[self.CONFIG_KEY_CONFIG])
                )
            except Exception as e:
                self.log(
                    f"Cannot create enricher {enricher_config[self.CONFIG_KEY_CLASS_NAME]} from {class_path}: {e}"
                )
        return enrichers

    def _load__and_create_enricher(self, class_path, class_name, enricher_config):
        """Try to load and instantiate the specified enricher."""
        enricher_spec = importlib.util.spec_from_file_location("log_enricher", class_path)
        enricher_module = importlib.util.module_from_spec(enricher_spec)
        enricher_spec.loader.exec_module(enricher_module)
        # enricher = enricher_module.__dict__[class_name](self._config)
        enricher = getattr(enricher_module, class_name)(enricher_config)
        if not issubclass(enricher.__class__, LogEnricherPlugin):
            raise Exception("Not a subclass of LogEnricherPlugin")
        return enricher

    def enrich_log(self, log_data):
        for plugin in self._enrichers:
            plugin.enrich_log(log_data)
