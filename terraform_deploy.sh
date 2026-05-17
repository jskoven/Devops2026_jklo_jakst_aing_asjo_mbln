#!/bin/bash
# if anything breaks just pull the plug immediately
set -e 

echo "Loading secrets..."
# check for secrets file
if [ -f secrets ]; then
    source secrets
else
    echo "❌ Error: 'secrets' file not found!"
    exit 1
fi

echo "Provisioning droplets..."
# initialize and build the whole cloud. auto-approve because we just want it to work without asking us a million questions
terraform init
terraform apply -auto-approve

echo "getting cluster data..."
# taking the fresh IPs out of terraform so we know where to send stuff
MANAGER_IP=$(terraform output -raw manager_ip)
MANAGER_PRIVATE_IP=$(terraform output -raw manager_private_ip)
WORKER_IP=$(terraform output -raw worker_ip)
DB_PRIVATE_IP=$(terraform output -raw db_private_ip)

echo "Manager Public IP: $MANAGER_IP"
echo "Worker Public IP:  $WORKER_IP"
echo "Database Private IP: $DB_PRIVATE_IP"

# droplets need a small timeout to initialize their docker engines (i think). 
# if we don't do this, the swarm join command will fail because the manager node isn't ready to accept it yet.
echo "Waiting 15 seconds for nodes..."
sleep 15

echo "Linking Worker to Swarm..."
# take the join token from the manager node over ssh. 
# StrictHostKeyChecking=no so it doesn't give us problems the first time we connect to the server and ask us if we want to add it to known_hosts.
SWARM_TOKEN=$(ssh -i ./ssh_key/terraform -o StrictHostKeyChecking=no root@$MANAGER_IP "docker swarm join-token worker -q")

# tell the worker to force join using the token. if it fails we just use || true so the script keeps moving
ssh -i ./ssh_key/terraform -o StrictHostKeyChecking=no root@$WORKER_IP "docker swarm join --token $SWARM_TOKEN $MANAGER_PRIVATE_IP:2377" || true

echo "Uploading configuration files to swarm..."
# make the directory on the server and scp the promtail yaml config up there so the swarm can see it
ssh -i ./ssh_key/terraform -o StrictHostKeyChecking=no root@$MANAGER_IP "mkdir -p promtail"
scp -i ./ssh_key/terraform -r ./remote_files/promtail/config.yml root@$MANAGER_IP:~/promtail/config.yml

echo "Deploying MiniTwit stack..."
# put the db private ip and docker username into the env, then pipe the docker-compose file into the swarm deploy command. this will replace the env vars in the compose file with the ones we just set, so the swarm can find the database and pull the images from dockerhub.
ssh -i ./ssh_key/terraform -o StrictHostKeyChecking=no root@$MANAGER_IP \
    "export DB_PRIVATE_IP=$DB_PRIVATE_IP && export DOCKER_USERNAME=$DOCKER_USERNAME && docker stack deploy -c - minitwit" < docker-compose-terraform.yml

echo "SUCCESS"
echo "App is at http://$MANAGER_IP:8080"
echo "Run terraform destroy -auto-approve to tear down the infrastructure"