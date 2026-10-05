# syntax=docker/dockerfile:1
FROM --platform=linux/arm64 node:22-slim AS builder

WORKDIR /build

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Clerk publishable key is inlined by Vite at BUILD time (VITE_* vars are
# baked into the bundle, not read at runtime). It is a public key — safe to
# pass as a build arg / GitHub Actions variable, not a secret. The build
# itself succeeds without it; the app only throws at runtime when missing.
ARG VITE_CLERK_PUBLISHABLE_KEY
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY

RUN npm run build

FROM --platform=linux/arm64 nginx:alpine AS runtime

COPY --from=builder /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
