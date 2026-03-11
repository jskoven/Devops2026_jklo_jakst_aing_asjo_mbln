#!/bin/bash
cd /minitwit

docker compose pull

docker compose up -d

docker image prune -f