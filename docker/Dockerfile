FROM python:2.7
ENV PYTHONUNBUFFERED 1

# Copy all files into the image.
COPY . /reactor-core

# Install reactor core and all dependencies.
RUN pip install /reactor-core/

# Expose ports.
EXPOSE 3000

# Set the default command to run reactor core in base image.
CMD python -m reactorcore.server