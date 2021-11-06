## pyweblogalyzer

Collect and analyze webserver access logs to provide web dashboards.

* Fully configurable, custom enrichers can be written and loaded to add custom data that can be used and visualized in dashboards with other log information.
* A single config file allows creating dashboards with datatables and graphs showing and parsing the information as wanted.
* Responsive layout, table and graphs for computers/mobile/tablets

See etc/config for example config file, dashboards, and enrichers that can be used with the docker image.

Note that the geoip databases are provided for example but should be updated. To get the free database, register and download the files see [link](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data). Keep the it up to date for correct results.

TODO: Documentation and tests, speed improvements, add config presets for common weblogs formats

### Screenshots

![Screenshot](https://github.com/vche/pyweblogalyzer/blob/master/etc/screen1.png)

![Screenshot](https://github.com/vche/pyweblogalyzer/blob/master/etc/screen2.png)

### Use docker image

Copy the config file example in etc/config/config.py to the folder you map to /config, optionally add your enrichers.
Update the config file according to your logs format (fields, datetime).

#### Docker

Example:
```
docker run -p 9333:9333 -v /home/pyweblogalyzer/etc/config -v /home/webserver/logs:/logs -v /home/pyweblogalyzer/etc/config:/geoipdb -d vche/pyweblogalyzer
```

#### Docker compose

Example:
```
pyweblogalyzer:
  image: vche/pyweblogalyzer
  container_name: pyweblogalyzer
  volumes:
    - /home/docker/pyweblogalyzer/etc/config:/config
    - /home/webserver/logs:/logs
    - /home/docker/pyweblogalyzer/etc/config:/config:/geoipdb
  ports:
    - 9333:9333
  restart: unless-stopped
```

### Development

TODO

#### Installing sources projects

Get the project and create the virtual env:
```sh
git clone https://github.com/vche/pyweblogalyzer.git
virtualenv pyvenv
. pyvenv/bin/activate
pip install -e .

PYWEBLOGALYZER_CONFIG=$PWD/etc/config/config.py pyweblogalyzer
```

Note: Entry points will be installed in pyvenv/bin, libs with pyvenv libs

#### Run tests

```sh
pip install tox
tox
```

#### Generate documentation:

```sh
pip install sphinx sphinx_rtd_theme m2r
./setup.py doc
```

In case new classes/modules are added, update the autodoc list:
```sh
rm  docs/sphinx_conf/source/*
sphinx-apidoc -f -o docs/sphinx_conf/source/ src/pyweblogalyzer --separate
```
