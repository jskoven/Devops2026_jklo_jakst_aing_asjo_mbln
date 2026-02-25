#!/bin/bash
# Load DOCKER_USERNAME from the .bash_profile we set up in the Vagrantfile
source ~/.bash_profile

cd /minitwit

ocker compose -f docker-compose.yml pull
docker compose -f docker-compose.yml up -d