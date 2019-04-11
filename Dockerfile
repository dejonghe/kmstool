FROM ubuntu:trusty
# Python requirements
RUN apt-get update && \
    apt-get install -y python python-dev python-pip gcc

# Setup KMS
ADD / /kmstool
WORKDIR /kmstool
RUN python setup.py sdist
RUN pip install dist/kmstool-*.tar.gz

# Prep workspace
RUN mkdir /workspace
WORKDIR /workspace
VOLUME /workspace
