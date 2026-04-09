#!/bin/bash
cd /minitwit || exit

docker pull ${DOCKER_USERNAME}/minitwitimage:latest

docker stack deploy -c docker-compose.yml minitwit --with-registry-auth

docker image prune -f