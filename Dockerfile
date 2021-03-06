FROM python:3.9.4-alpine3.13

# basic build dependencies
RUN apk add --no-cache --virtual .build-deps gcc g++ postgresql-dev musl-dev python3-dev
RUN apk add libpq

# add an install our source code
COPY src/ /src/
COPY tests/ /tests/
COPY setup.py /setup.py
COPY requirements.txt /requirements.txt
COPY README.md /README.md
RUN python -m pip install --upgrade pip
RUN pip install -e /

# clean-up
RUN apk del --no-cache .build-deps

WORKDIR /src

