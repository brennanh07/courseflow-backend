# syntax=docker/dockerfile:1.4

FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    nano \
    gcc \
    musl-dev \
    default-libmysqlclient-dev \
    pkg-config \
    libffi-dev \
    make && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
