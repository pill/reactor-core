# Creating a Dockerized Reactor Core based micro service

## Create a Dockerfile for your app
I usually put it in `/docker/app/Dockerfile`

Example
```
# Use latest version of reactor-core as base image.
FROM 339626119775.dkr.ecr.us-east-1.amazonaws.com/dna-core/reactor-core:latest

# Add microservice application and tests.
RUN mkdir /code
COPY ./my_project /code/my_project
COPY ./tests /code/tests

RUN pip install -U pip setuptools

COPY ./requirements.txt ./
RUN pip install -r ./requirements.txt

WORKDIR /code

EXPOSE 3000

CMD python -m my_project.api.server
```

__Note:__ You will need `/code` on your PYTHONPATH wherever you run the server (may need to be specified in other environments). In this case `WORKDIR=/code` takes care of it. CMD to run is the server file defined in your app.

## Local Docker setup
### docker-compose
Create a `docker-compose.yml` to configure environment vars, ports, volumes mapped from your computer into containers, etc.
```
version: '2.1'
services:
  redis:
    image: redis:latest
    ports:
        - 6379:6379
    command: --appendonly yes
    volumes:
        - data:/data
  app:
    restart: always
    #image: 339626119775.dkr.ecr.us-east-1.amazonaws.com/my_project/my_project-api/app:1.45
    build: "./docker/app"
    ports:
        - 3000:3000
    volumes:
        - ./docker/app:/code
    command: /bin/bash -c "sleep 3 && python -m my_project.api.server"
    depends_on:
        - redis
    environment:
        - ENV=development
        - PYTHONUNBUFFERED=1
        - PYTHONPATH=/code
        - REDIS_HOST=192.168.99.100
        - REDIS_PORT=6379
        - REDIS_DB=0
        - REDIS_TIMEOUT=5
    networks:
        - my_project
        - default

networks:
    my_project:
        external: true
    default:

volumes:
    data:
    db:
```

When you are working locally, you can use the `build` configuration key for your app to point to your `/docker/app/Dockerfile`.

Currently Redis must be configured in order for the server to run correctly.

### Start the server
```
docker-compose up
```

Access the server at `http://192.168.99.100:3000`.
Use whatever IP your docker-machine is running on and whatever port your app is running on.



