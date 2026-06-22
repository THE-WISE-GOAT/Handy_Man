FROM node:22-alpine AS dev

WORKDIR /app

COPY worker_app/package*.json ./worker_app/
RUN npm install --prefix ./worker_app

WORKDIR /app/worker_app

EXPOSE 5174

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5174"]

FROM node:22-alpine AS build

WORKDIR /app

COPY worker_app/package*.json ./worker_app/
RUN npm install --prefix ./worker_app

COPY shared ./shared
COPY worker_app ./worker_app

WORKDIR /app/worker_app

ARG VITE_API_URL=http://localhost:8000
ARG VITE_CUSTOMER_URL=http://localhost:5173
ARG VITE_MAP_STANDALONE_URL=http://localhost:5174

ENV VITE_API_URL=$VITE_API_URL \
    VITE_CUSTOMER_URL=$VITE_CUSTOMER_URL \
    VITE_MAP_STANDALONE_URL=$VITE_MAP_STANDALONE_URL

RUN npm run build

FROM nginx:1.27-alpine AS production

COPY worker_app/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/worker_app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
