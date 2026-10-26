# iti-ai-console: the ITI AI Console (step 9.5.3). Build from the repo root:  docker build -t iti-ai-console:dev admin-ui
# ITI_API_URL and CONSOLE_COOKIE_SECURE are read when the server starts (compose / docker run), never baked in here.

# --- Stage 1: install the exact packages from package-lock.json ---
FROM node:24.21.0-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci --no-audit --no-fund

# --- Stage 2: build the standalone server (next.config.ts: output "standalone") ---
FROM node:24.21.0-bookworm-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# --- Stage 3: the image that runs: the standalone server and its static files, nothing else ---
FROM node:24.21.0-bookworm-slim
WORKDIR /app
# HOSTNAME: Docker sets it to the container id; the Next.js server must listen on every address inside the container.
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0 TZ=Asia/Manila
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:3000/login').then(r => process.exit(r.ok ? 0 : 1), () => process.exit(1))"
CMD ["node", "server.js"]