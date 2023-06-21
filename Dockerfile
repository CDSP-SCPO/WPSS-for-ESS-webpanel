##########
# NODE BUILDER

FROM node:16-alpine AS nbuilder
WORKDIR /frontend/
RUN mkdir /frontend/static/ && mkdir /frontend/static/lib

COPY package*.json /frontend/
RUN npm install

RUN cp /frontend/node_modules/bootstrap/dist/js/bootstrap.bundle.js /frontend/static/lib/
RUN cp -r /frontend/node_modules/bootstrap-icons/icons/ /frontend/static/icons/
COPY frontend/scss/ /frontend/scss/
RUN npm run build


##########
# PYTHON BUILDER

# Create venv with python requirements
FROM python:3.10-alpine as pybuilder
RUN python -m venv /.venv/
RUN apk add --no-cache gcc musl-dev postgresql-dev g++
COPY requirements*.txt /qxsms/
RUN /.venv/bin/pip install --no-cache-dir -r /qxsms/requirements.txt


##########
# MAIN

FROM python:3.10-alpine
# Make app root directory
WORKDIR /qxsms/
RUN adduser -D qxsms -h /qxsms/

# Add venv to path
ENV PATH="/.venv/bin:$PATH"
# Install and get python dependencies
RUN apk add --no-cache postgresql-dev gettext
COPY --from=pybuilder /.venv/ /.venv/

# Get generated css and bootstrap.native js
COPY --from=nbuilder /frontend/static/ /qxsms/static/

# Add the source code in the container
COPY --chown=qxsms:qxsms . /qxsms/

USER qxsms

# Env variable created at build time to be able to get the version without .git
ARG QXSMS_VERSION
ENV QXSMS_VERSION=$QXSMS_VERSION
