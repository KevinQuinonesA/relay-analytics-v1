FROM node:20.18.1-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# Tests run from a copy of the sources (no bind mount, so nothing root-owned lands on the host)
FROM deps AS test
COPY . .
CMD ["npm", "test"]

FROM deps AS build
COPY . .
RUN npm run build

FROM nginx:1.27.3-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
