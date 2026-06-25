FROM node:22-alpine AS dev

WORKDIR /app

COPY user_app/package*.json ./user_app/
RUN npm install --prefix ./user_app

WORKDIR /app/user_app

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

FROM node:22-alpine AS build

WORKDIR /app

COPY user_app/package*.json ./user_app/
RUN npm ci --prefix ./user_app

COPY shared ./shared
COPY user_app ./user_app

WORKDIR /app/user_app

ARG VITE_API_URL=http://localhost:8000
ARG VITE_MAP_STANDALONE_URL=

ENV VITE_API_URL=$VITE_API_URL \
    VITE_MAP_STANDALONE_URL=$VITE_MAP_STANDALONE_URL

RUN npm run build

FROM nginx:1.27-alpine AS production

COPY user_app/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/user_app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
