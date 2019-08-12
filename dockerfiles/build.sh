sudo docker build -t os-k8s-node .
sudo docker tag os-k8s-node:latest zangrand/os-k8s-node:latest
sudo docker push zangrand/os-k8s-node:latest
