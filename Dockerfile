FROM debian:12-slim

RUN apt update

RUN apt install -y gcc make
RUN apt install -y linux-perf
RUN apt install -y hwloc

RUN apt install -y python3 python3-pip python-is-python3

COPY src/requirements.txt tmp/requirements.txt
RUN pip install -r tmp/requirements.txt --break-system-packages

