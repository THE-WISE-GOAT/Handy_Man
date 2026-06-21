FROM node:22-alpine AS dev

WORKDIR /app

COPY customer_app/package*.json ./customer_app/
RUN npm ci --prefix ./customer_app

WORKDIR /app/customer_app

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

FROM node:22-alpine AS build

WORKDIR /app

COPY customer_app/package*.json ./customer_app/
RUN npm ci --prefix ./customer_app

COPY shared ./shared
COPY customer_app ./customer_app

WORKDIR /app/customer_app

ARG VITE_API_URL=http://localhost:8000
ARG VITE_WORKER_URL=http://localhost:5174
ARG VITE_MAP_STANDALONE_URL=http://localhost:5174

ENV VITE_API_URL=$VITE_API_URL \
    VITE_WORKER_URL=$VITE_WORKER_URL \
    VITE_MAP_STANDALONE_URL=$VITE_MAP_STANDALONE_URL

RUN npm run build

FROM nginx:1.27-alpine AS production

COPY customer_app/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/customer_app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
