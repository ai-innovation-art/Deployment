# syntax=docker/dockerfile:1
# Unprivileged nginx: runs as non-root and listens on 8080 (not 80).
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY html/ /usr/share/nginx/html/
EXPOSE 8080
