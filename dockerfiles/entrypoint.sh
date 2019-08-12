#!/bin/bash
set -e

cp $OS_KEY_CERT cert.pem
chmod 600 cert.pem

eval "$(ssh-agent -s)"
ssh-add cert.pem

cd ansible-k8s

export OS_VM_NAME=$OS_VM_NAME-$(($(date +%s%N)/1000000))

ansible-playbook deploy_node_openstack.yaml
