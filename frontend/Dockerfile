# frontend/Dockerfile

# ===== Stage 1: Build =====
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# ===== Stage 2: Serve =====
FROM nginx:alpine AS production

RUN apk add --no-cache gettext

ENV FRONTEND_API_BASE_URL=/api/v1

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY config.js.template /etc/nginx/templates/config.js.template
COPY docker-entrypoint.d/40-generate-runtime-config.sh /docker-entrypoint.d/40-generate-runtime-config.sh

RUN chmod +x /docker-entrypoint.d/40-generate-runtime-config.sh

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
