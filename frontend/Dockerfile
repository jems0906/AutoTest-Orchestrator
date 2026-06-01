FROM nginx:alpine

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY index.html /usr/share/nginx/html/index.html
COPY app.js /usr/share/nginx/html/app.js
COPY styles.css /usr/share/nginx/html/styles.css
COPY 10-generate-config.sh /docker-entrypoint.d/10-generate-config.sh

RUN chmod +x /docker-entrypoint.d/10-generate-config.sh