# syntax=docker/dockerfile:1.7

# Stage 1: Build the React application
FROM node:20-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json* ./

RUN npm install --legacy-peer-deps

COPY . .
COPY --from=api-spec frontend.yaml ../api-specification/frontend.yaml

RUN npm run build

# Stage 2: Serve with nginx (also reverse-proxies API routes to backend)
FROM nginx:alpine AS runner

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
