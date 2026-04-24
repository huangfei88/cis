FROM nginx:alpine
COPY nginx.conf /etc/nginx/nginx.conf
# TLS certificates are mounted at runtime via docker-compose volume
RUN mkdir -p /etc/nginx/certs
