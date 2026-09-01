FROM nginx:1.23.3-alpine

# removing default configuration of nginx
RUN rm /etc/nginx/conf.d/default.conf 

# adding custom conf. for nginx
COPY ./default.conf /etc/nginx/conf.d/default.conf