FROM python:3.9-slim

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY . .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN python setup.py install
