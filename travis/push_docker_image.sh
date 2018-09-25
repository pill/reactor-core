#!/bin/bash
# Upload the application image to Dockerhub.
set -e

# Get passed arguments.
TRAVIS_TAG="$1"
DOCKER_REPO_LOCATION="$2"

# Tag the image.
docker tag reactor-core-local:0.0 ${DOCKER_REPO_LOCATION}:${TRAVIS_TAG}
docker tag reactor-core-local:0.0 ${DOCKER_REPO_LOCATION}:latest
docker images

# Push the image, both the tag version and the latest tag.
docker push ${DOCKER_REPO_LOCATION}:${TRAVIS_TAG}
docker push ${DOCKER_REPO_LOCATION}:latest
