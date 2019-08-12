FROM ubuntu:18.04
MAINTAINER Lisa Zangrando <lisa.zangrando@pd.infn.it>
RUN apt-get update && \
    apt-get install --no-install-recommends -y software-properties-common && \
    apt-add-repository ppa:ansible/ansible && \
    apt-get update && \
    apt-get install -y ansible python-pip

RUN rm -rf /var/lib/apt/lists/*

RUN pip install shade

COPY ./ansible-k8s ./ansible-k8s
COPY ./entrypoint.sh ./entrypoint.sh

ENTRYPOINT ./entrypoint.sh
