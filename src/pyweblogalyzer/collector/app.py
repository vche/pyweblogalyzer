import logging
import os
import time
import parse
# import pandas
import ipapi
import user_agents

from datetime import datetime
from ipaddress import ip_address, ip_network
from os import path
from threading import Thread
from pyweblogalyzer.dataset.weblogdata import WebLogData
from .enrichers import LogEnrichers


class CollectorApp(Thread):
    LOG_KEY_REMOTE_ADDR = "remote_ip"
    LOG_KEY_DATETIME = "datetime"
    LOG_KEY_REQUEST = "request"
    LOG_KEY_STATUS = "status"
    LOG_KEY_BYTES_SENT = "bytes_sent"
    LOG_KEY_HTTP_REFERER = "referer"
    LOG_KEY_HOSTNAME = "hostname"
    LOG_KEY_USER_AGENT = "user_agent"
    LOG_KEY_REQUEST_TIME = "request_time"

    def __init__(self, dataset, config):
        super().__init__(name=__name__, daemon=True)
        self._log_positions = {}
        self._geoip_cache = {}
        self._config = config
        self.log = logging.getLogger(__name__)
        self._dataset = dataset
        self._running = False
        self._period = self._config['COLLECTION_DELAY_SECS']
        self._log_parser = parse.compile(self._config['LOG__FORMAT'])
        self._dt_parser = self._config['LOG_DATE_TIME_FORMAT']
        self._enricher = LogEnrichers(config)
        self._local_networks = [ip_network(local_net) for local_net in self._config['LOCAL_NETWORKS']]


    def run(self):
        """Run the thread periodically polling log files."""
        self._running = True
        while self._running:
            self.log.info("Collector running")

            logfiles = self._build_file_list()
            for logfile in logfiles:
                # TODO: async reading of all files ?
                self._parse_log_file(logfile)

            self.log.info("Collector finished")
            time.sleep(self._period)

    def _build_file_list(self):
        """Build the list of log files to parse."""
        config_path = self._config['WEB_LOG_PATH']
        if path.isfile(config_path):
            return [config_path]
        elif path.isdir(config_path):
            # TODO get list of filenames matching access log in the folder
            raise NotImplementedError("Specified config log path is not a file")
        else:
            raise ValueError(f"No log files found in {self._config['WEB_LOG_PATH']}")

    def _parse_log_file(self, logfile):
        """Load and parse all new logs in the specified file."""
        # Get the last read position in this file, or read from start if new file
        last_pos = self._log_positions.get(logfile, 0)
        try:
            with open(logfile, "r") as file:
                # Set the file pointer, read from start if the last pos exceeds the file, it means the file has changed
                if last_pos > os.fstat(file.fileno()).st_size:
                    last_pos = 0
                file.seek(last_pos)

                # Read all new lines and update final position in file
                log_line = file.readline()
                while log_line:
                    try:
                        self._parse_log_line(log_line.strip())
                    except Exception as e:
                        self.log.error(f"Error parsing log {log_line}: {e}")
                    log_line = file.readline()
                self._log_positions[logfile] = file.tell()
        except Exception as e:
            self.log.error(f"Error reading log file {logfile}: {e}")

    def is_remote_ip(self, ip_str):
        # If the ip is loopback, v6, or v4 to local network, it is not remote
        client_ip = ip_address(ip_str)
        if client_ip.is_loopback or client_ip.version == 6:
            return False
        for local_net in self._local_networks:
            if client_ip in local_net:
                return False
        return True

    def _get_geoloc(self, ipaddr):
        IPAPI_RATE_LIMITER_WAIT = 1.0
        DEFAULT_VALUES = {'city': "unknown", 'country_name': "unknown", 'latitude': 0.0, 'longitude': 0.0}

        # return DEFAULT_VALUES
        if not ipaddr or not self.is_remote_ip(ipaddr):
            return DEFAULT_VALUES
        # Get geo info from cache, or fill it
        if ipaddr in self._geoip_cache:
            return self._geoip_cache[ipaddr]
        else:
            try:
                geoloc = ipapi.location(ipaddr)
            except ipapi.exceptions.RateLimited:
                self.log.warning(f"ipapi rate limitation reached, waiting {IPAPI_RATE_LIMITER_WAIT}s")
                time.sleep(IPAPI_RATE_LIMITER_WAIT)
                try:
                    geoloc = ipapi.location(ipaddr)
                except ipapi.exceptions.RateLimited:
                    self.log.warning("Geoloc throttled")
                    return DEFAULT_VALUES
            self._geoip_cache[ipaddr] = geoloc
            return geoloc

    def _is_excluded(self, parsed_log):
        """Check if a log is configured to be ignored."""
        for filter in self._config["EXCLUDE_REQUESTS"]:
            if filter in parsed_log[self.LOG_KEY_REQUEST]:
                # TODO:Increment statistics of ignored reauest for filter parsed_log[self.LOG_KEY_REQUEST]
                return True
        if parsed_log[self.LOG_KEY_REQUEST] in self._config["EXCLUDE_REMOTE_IP"]:
            # TODO:Increment statistics of ignored reauest for filter parsed_log[self.LOG_KEY_REQUEST]
            return True
        else:
            return False

    def _parse_log_line(self, log_line):
        """Execute the command, and process the results."""
        parsed_log = self._log_parser.parse(log_line)

        # Extract info according to custom format configured
        if not parsed_log:
            self.log.error("Log entry not matching configured format: {log_line}")
            return

        if self._is_excluded(parsed_log):
            return

        # Enrich basic information
        geoloc = self._get_geoloc(parsed_log[self.LOG_KEY_REMOTE_ADDR])
        operation, url, protocol = parsed_log[self.LOG_KEY_REQUEST].split()
        user_agent = user_agents.parse(parsed_log[self.LOG_KEY_USER_AGENT])

        # Create a new data entry
        log_data = WebLogData(
            remote_ip=parsed_log[self.LOG_KEY_REMOTE_ADDR],
            http_referer=parsed_log[self.LOG_KEY_HTTP_REFERER],
            hostname=parsed_log[self.LOG_KEY_HOSTNAME],
            # timestamp=pandas.to_datetime(parsed_log[self.LOG_KEY_DATETIME], format=self._dt_parser),
            timestamp=datetime.strptime(parsed_log[self.LOG_KEY_DATETIME], self._dt_parser),
            bytes_sent=int(parsed_log[self.LOG_KEY_BYTES_SENT]),
            request_time=float(parsed_log[self.LOG_KEY_REQUEST_TIME]),
            request_status=int(parsed_log['status']),
            city=geoloc.get('city'),
            country=geoloc.get('country_name'),
            lat=geoloc.get('latitude'),
            long=geoloc.get('longitude'),
            http_operation=operation,
            http_url=url,
            protocol=protocol,
            browser=user_agent.browser.family,
            os=user_agent.os.family,
            device=user_agent.device.family,
        )

        # Run custom enrichers
        self._enricher.enrich_log(log_data)

        # Append to the global dataset
        self._dataset.add(log_data)
