# Deployment of a Kubernetes cluster via ansible

## Overview
The provided Ansible playbooks allow you to deploy a Kubernetes cluster both on bare metal and on an OpenStack cloud.
The installation is based on the kubeadm tool configured with a pre-generated admin token and flannel network.
The playbooks enrich the cluster installation with a set of services such as:
- dashboards: legacy and Grafana
- monitoring: Prometheus Operator
- Big Data: Spark and Apache Kafka operators.

## System requirements
The deployment environment requires:
- Ansible 2.5.x (2.7.x not yet fully supported)
- Ubuntu 18.04
- Master and nodes must have passwordless SSH access

## Getting Started
This section represents a quick installation and is not intended to teach you about all the components. The easiest way to get started is to clone the 'ansible-k8s' repository:

```
# git clone https://github.com/zangrand/ansible-k8s.git
# cd ansible-k8s
```

The directory structure should be like

```
ansible-k8s/
├── config
│   ├── config
│   ├── keystone_client.py
│   └── tls-ca-bundle.pem
├── deploy_k8s.yaml
├── deploy_master_openstack.yaml
├── deploy_node_openstack.yaml
├── group_vars
│   └── all
├── inventory
├── k8s
│   ├── alertmanager-service.yaml
│   ├── dashboard-setup.yaml
│   ├── grafana-service.yaml
│   ├── os-k8s-node.yaml
│   └── prometheus-service.yaml
├── openstack_config.yaml
├── README.md
└── roles
    ├── auth
    │   └── keystone
    │       ├── files
    │       │   ├── infn_ca.pem
    │       │   ├── k8s-auth-policy.yaml
    │       │   ├── k8s-keystone-auth.yaml
    │       │   ├── k8s-keystone-auth.yaml_orig
    │       │   ├── keystone_client.py
    │       │   ├── tls-ca-bundle.pem
    │       │   └── webhookconfig.yaml
    │       └── tasks
    │           └── main.yml
    ├── common
    │   └── tasks
    │       └── main.yml
    ├── docker
    │   └── tasks
    │       └── main.yml
    ├── kubeadm
    │   └── tasks
    │       └── main.yml
    ├── master
    │   ├── handlers
    │   │   └── main.yml
    │   └── tasks
    │       └── main.yml
    ├── node
    │   └── tasks
    │       └── main.yml
    ├── os-node
    │   └── tasks
    │       └── main.yml
    ├── prometheus
    │   └── tasks
    │       └── main.yml
    └── spark
        └── tasks
            └── main.yml
```

## Deployment on bare metal

The hosts on which your Kubernetes cluster will be deployed must already exist and have passwordless SSH access.
Please, edit the inventory file properly by specifying the IP addresses of master and nodes:

```
[master]
master1 ansible_host=10.64.41.16

[node]
node1 ansible_host=10.64.41.11
node2 ansible_host=10.64.41.12
node3 ansible_host=10.64.41.15
...
```

Add your SSH key to the ssh-agent

```
# eval "$(ssh-agent -s)"
Agent pid 59566

# ssh-add ~/.ssh/id_rsa
```
or
```
# ssh-add your_cert.pem
```

Finally execute:

```
# ansible-playbook -i inventory deploy_k8s.yaml
```

## Deployment on an OpenStack cloud

It is supposed the hosts on which your Kubernetes cluster will be deployed NOT already exist. The provided Ansible playbook is able to create and configure properly all hosts (i.e. VMs) on an OpenStack cloud and deploy Kubernetes on them.
To do it, edit the file openstack_config.yaml and fill up all required attributes (i.e. OS_AUTH_URL, OS_PROJECT_NAME, OS_USERNAME, etc), the same used for accessing OpenStack by its client. Moreover, please define the VMs characteristics of the master and nodes, in terms of name, flavor, and image. Finally, specify the number of nodes (i.e. OS_NODES) is expected to be composed of your cluster.

Verify if the 'shade' Python module is available on your environment, otherwise install it:

```
$ pip install shade
```

Add your SSH private key to the ssh-agent. Please use the same key associated to your OpenStack Key Pair and by which you can login your VM using ssh -i cloud.key <username>@<instance_ip>

```
# eval "$(ssh-agent -s)"
Agent pid 59566

# ssh-add cloud.key
```
or
```
# ssh-add your_cert.pem
```

Finally execute:

```
# ansible-playbook deploy_master_openstack.yaml
```
Please remark that deployment requires further a few minutes to have the full cluster up and running.


## How to access your Kubernetes cluster 

There are two different ways to access the Kubernetes cluster: by the kubectl or by the dashboard.

### By kubectl 
The kubectl command line tool is available on the master node. If you wish to access the cluster remotely please see the following guide: https://kubernetes.io/docs/tasks/tools/install-kubectl/.
In case of Kubernetes has been deployed on OpenStack, you can enable your local kubectl to access the cluster through the Keystone authentication. To do it, copy all files contained into the folder ansible-k8s/config/ to $HOME/.kube/ . The tls-ca-bundle.pem file is CA certificate required by the CloudVeneto OpenStack base cloud. Do not forget to source the openrc.sh with your Openstack credentials and OS_CACERT variable set. Please use your CA certificate, if required.
Edit $HOME/.kube/config and set the IP address of your new K8S master.


### By dashboards
The cluster exposes the following dashboards:
- K8S dashboard: https://<master_ip>:30900
- Prometheus UI: http://<master_ip>:30901
- Alertmanager UI: http://<master_ip>:30902
- Grafana UI: http://<master_ip>:30903

To login into the K8S dashboard use the token of the kube-system:default service account. To get it, execute the following command at the master node:

```
# kubectl -n kube-system describe secret kubernetes-dashboard
...
Data
====
ca.crt:     1025 bytes
namespace:  11 bytes
token:      eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJrdWJlLXN5c3RlbSIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJrdWJlcm5ldGVzLWRhc2hib2FyZC10b2tlbi05cGc5NyIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50Lm5hbWUiOiJrdWJlcm5ldGVzLWRhc2hib2FyZCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6IjAyYjYzZGRkLWFhYzItMTFlOC1iNTBkLWZhMTYzZTQ2OWU0ZiIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDprdWJlLXN5c3RlbTprdWJlcm5ldGVzLWRhc2hib2FyZCJ9.XPSzu31SvkR_xwfd3MpLQBkHc7anZlEA1FMSMrZsU6wENflLJQEPrEUJmYji24jU4vTnd2eVK1rhEB4P1iPEiVg0nCZIIhkJTtpaNTyefV1Uq3V9JUTxEO9rMAsfSx16yqctuSi9qgUU7Ac85ZEffJqrKrQwSkQGyCnrDuAQ11Ryl5VGWbTfTfeEP-epjm0jnAcI1akhkoS2xUESRV9Bq41rOtboJYv3hAe0pjOL7CHZ3mTsHMHXR_0IDQvCTx8tC9S_vU09-jK8c_4UAkoUDd5-_1DPl68AckAMtgZyPSQLKnlFW50WwQt5WCwp7VGrBL_okM-E7QeTQkrUMrGTDw
```

To login into the Grafana dashboard as administrator use the credential: username=admin and password=admin. The first login requires the changing of the default password for security reasons.
