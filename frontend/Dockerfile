# ===== Stage 1: Build =====
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# ===== Stage 2: Serve =====
FROM nginx:alpine AS production

# Копируем собранный фронт
COPY --from=builder /app/dist /usr/share/nginx/html

# Копируем конфиг nginx для SPA
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]