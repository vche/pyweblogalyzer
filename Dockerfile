# FROM python:3
FROM ubuntu:focal

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-pip \
        && \
        rm -rf /var/cache/apt /var/lib/apt/lists
ADD src/ /src
ADD setup.py /
ADD setup.cfg /
ADD src/pyweblogalyzer/config.py /config/
ENV PYWEBLOGALYZER_CONFIG /config/config.py

RUN pip3 install virtualenv
RUN virtualenv /pyvenv

# Install dependencies:
WORKDIR /
RUN /pyvenv/bin/pip -v install -e .

# Run the application:
CMD ["/pyvenv/bin/pyweblogalyzer", "2>&1"]

VOLUME /config
VOLUME /logs
EXPOSE 9333
