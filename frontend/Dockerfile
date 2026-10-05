FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Proxy /api to the backend service so the SPA talks to the API container.
RUN printf 'server {\n  listen 80;\n  location / { root /usr/share/nginx/html; try_files $uri /index.html; }\n  location /api { proxy_pass http://backend:8000; }\n}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
