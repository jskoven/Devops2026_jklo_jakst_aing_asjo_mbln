#!/bin/bash
source /root/.bash_profile

# 1. Pull the newest image that GitHub Actions just pushed
docker pull ${DOCKER_USERNAME}/minitwitimage:latest

# 2. Stop and remove the old container
docker stop minitwit || true
docker rm minitwit || true
docker image prune -f

# 3. Run the new version
# We mount /tmp to /data because Vagrant puts the DB in /tmp
docker run -d \
  --name minitwit \
  -p 80:5001 \
  -v /tmp:/data \
  -e "DATABASE_PATH=/data/minitwit.db" \
  ${DOCKER_USERNAME}/minitwitimage:latest