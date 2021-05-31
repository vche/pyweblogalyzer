import logging

import pyweblogalyzer
from pyweblogalyzer import CollectorApp, DashboardApp, WebLogDataSet
from importlib import metadata

ENVVAR_CONFIG="PYWEBLOGALYZER_CONFIG"
log = logging.getLogger(__name__)


def setup_logging(logfile=None, loglevel=logging.INFO):
    logging.basicConfig(
        filename=logfile or None,
        level=loglevel,
        format="[%(levelname)-7s %(asctime)s %(name)s,%(filename)s:%(lineno)d] %(message)s",
    )


def main() -> None:
    """Main entry point."""
    dataset = WebLogDataSet()
    dashboard = DashboardApp(dataset, "pyweblogalyzer.config.Config", ENVVAR_CONFIG)
    collector = CollectorApp(dataset, dashboard.config)
    setup_logging(logfile=dashboard.config["LOG_FILE"], loglevel=dashboard.config.get("LOG_LEVEL"))
    log.info(f"Started pyweblogalyzer {metadata.version('pyweblogalyzer')}")

    # Todo: start flask in a thread, so that we can kill the other task if one stops,
    # or pass the collector task to the dashboard app ?
    collector.start()
    dashboard.run()


if __name__ == "__main__":
    main()
