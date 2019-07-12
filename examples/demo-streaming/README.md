## Streaming processing example with Apache Kafka and Spark
This example is taken from M. Migliorini stuff (some [scripts in Dropbox](https://www.dropbox.com/sh/yuovx54mmlf79ce/AABSjO-2U7nKIE1gXKs752Jra?dl=0) and scala code at https://github.com/Mmiglio/binaryStream).

The demo assumes that you already created a K8s cluster with both Spark and Kafka operators deployed, according with the instructions 
at https://github.com/zangrand/ansible-k8s

The relevant K8s commands are in https://github.com/zangrand/ansible-k8s/blob/master/examples/demo-streaming/demo.sh file. You just need to replace in streamprocessor.yaml file the mainApplicationFile line with your StreamProcessing-1.0-SNAPSHOT.jar link, after having rebuild it with the right Kafka broker IP:Port hardcoded.

The streamprocessor.yaml file represents the SparkApplication object defined to launch the Spark application through the Spark operator, and is somehow the "translation" of the launchSpark.sh script into the Spark operator language. 
