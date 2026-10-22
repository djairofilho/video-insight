# O workflow compila e testa dist/ antes de criar a imagem.
FROM nginx:stable-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY dist/ /usr/share/nginx/html/
RUN nginx -t
EXPOSE 80
