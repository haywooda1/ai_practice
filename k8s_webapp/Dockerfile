FROM nginx:latest

COPY index.html /usr/share/nginx/html/index.html

RUN chown nginx:nginx /usr/share/nginx/html/index.html

RUN chown -R nginx:nginx /var/cache/nginx /var/run \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

USER nginx
