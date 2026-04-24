# Security-hardened ansible-runner execution image
# Runs as non-root uid=1000, receives scripts via base64-encoded env vars
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ansible \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir ansible-runner==2.4.0

# SECURITY: non-root execution user
RUN groupadd -g 1000 runner && \
    useradd -u 1000 -g runner -s /sbin/nologin -M runner

WORKDIR /runner

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER 1000:1000

ENTRYPOINT ["/entrypoint.sh"]
