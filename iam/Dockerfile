# ── Stage 1: base (pnpm via corepack) ────────────────────────────────────────
FROM node:20-alpine AS base
RUN corepack enable && corepack prepare pnpm@9 --activate
WORKDIR /app

# ── Stage 2: dependencies ─────────────────────────────────────────────────────
FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# ── Stage 3: builder ──────────────────────────────────────────────────────────
FROM base AS builder
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* vars are baked into the bundle at build time
ARG NEXT_PUBLIC_TURNSTILE_SITE_KEY
ENV NEXT_PUBLIC_TURNSTILE_SITE_KEY=$NEXT_PUBLIC_TURNSTILE_SITE_KEY

RUN ./node_modules/.bin/prisma generate
RUN pnpm build

# ── Stage 4: runner ───────────────────────────────────────────────────────────
FROM base AS runner

RUN apk add --no-cache curl

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=5000 \
    HOSTNAME=0.0.0.0

# Copy the entire built app — pnpm uses .pnpm/ symlink targets so we need
# the full node_modules tree, not selective copies.
COPY --from=builder /app ./

EXPOSE 5000

# Apply pending migrations then start the server.
# To seed the first superadmin after initial deploy, run:
#   docker compose -f docker-compose.prod.yml exec iam pnpm seed:admin
CMD ["sh", "-c", "./node_modules/.bin/prisma migrate deploy --schema ./prisma/schema/schema.prisma && pnpm start"]
