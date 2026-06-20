FROM node:22-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        libpq-dev \
        python3 \
        python3-dev \
        python3-pip \
        python3-venv \
    && python3 -m venv /opt/venv \
    && ln -sf /opt/venv/bin/python3 /opt/venv/bin/python \
    && printf '#!/bin/sh\nexec /opt/venv/bin/python "$@"\n' > /usr/local/bin/python \
    && printf '#!/bin/sh\nexec /opt/venv/bin/pip "$@"\n' > /usr/local/bin/pip \
    && chmod +x /usr/local/bin/python /usr/local/bin/pip \
    && groupadd --system fralib \
    && useradd --system --gid fralib --home-dir /app --shell /usr/sbin/nologin fralib \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r /tmp/requirements.txt

COPY . /app

RUN mkdir -p /var/www/fralib/sites /app/logs /tmp/fralib_builder \
    && chown -R fralib:fralib /app /var/www/fralib /tmp/fralib_builder

EXPOSE 8000

USER fralib

CMD ["python", "server.py"]
