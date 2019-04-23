# deploy kafka cluster:
kubectl apply -f smactcluster.yaml
#
# define the topics:
kubectl apply -f topics.yaml
#
# find the endpoints to set in bootstrap.servers parameter and then exec the bin/kafka-run-class.sh inside kafka to populate# the kafka topic porduce28partitions:
BSERV=$(kubectl describe service smactcluster-kafka-external-bootstrap | grep Endpoints | awk '{print $2}')
kubectl exec -it smactcluster-kafka-0 -- bin/kafka-run-class.sh org.apache.kafka.tools.ProducerPerformance --topic produce28partitions --num-records 10000000000 --record-size 32 --throughput 100 --producer-props compression.type=snappy acks=1 bootstrap.servers=$BSERV buffer.memory=104857600 batch.size=50000
#
# get K8s master IP and kafka bootstrap port to be put in "val brokers" line of KafkaClientProperties.scala:
kubectl get node master -o=jsonpath='{.status.addresses[0].address}{"\n"}'
kubectl get service smactcluster-kafka-external-bootstrap -o=jsonpath='{.spec.ports[0].nodePort}{"\n"}'
#
# launch the spark application:
kubectl apply -f streamprocessor.yaml
#
# check the status:
kubectl get pod -w
#
# look at the spark executor log:
STEX=$(kubectl get pod | grep streamprocessor | grep exec | awk '{print $1}')
kubectl logs -f $STEX | grep produce28partitions
