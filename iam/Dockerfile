# ── Stage 1: dependencies ─────────────────────────────────────────────────────
FROM node:20-alpine AS deps

RUN npm install -g pnpm@9

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# ── Stage 2: builder ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

RUN npm install -g pnpm@9

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* vars are baked into the bundle at build time
ARG NEXT_PUBLIC_TURNSTILE_SITE_KEY
ENV NEXT_PUBLIC_TURNSTILE_SITE_KEY=$NEXT_PUBLIC_TURNSTILE_SITE_KEY

# Generate the Prisma client (uses prisma.config.ts — schema at ./prisma/schema/schema.prisma)
RUN ./node_modules/.bin/prisma generate

RUN pnpm build

# ── Stage 3: runner ───────────────────────────────────────────────────────────
FROM node:20-alpine AS runner

RUN apk add --no-cache curl

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=5000 \
    HOSTNAME=0.0.0.0

# Standalone server output
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Generated Prisma client (custom output — prisma/generated/prisma)
# Copying explicitly because wasm files are not traced by nft
COPY --from=builder /app/prisma/generated ./prisma/generated

# Prisma CLI + engines for running migrate deploy on startup
COPY --from=builder /app/node_modules/prisma ./node_modules/prisma
COPY --from=builder /app/node_modules/@prisma ./node_modules/@prisma
COPY --from=builder /app/node_modules/.bin/prisma ./node_modules/.bin/prisma

# Schema file needed by migrate deploy
COPY --from=builder /app/prisma/schema/schema.prisma ./prisma/schema/schema.prisma

EXPOSE 5000

# Apply pending migrations then start the server.
# To seed the first superadmin after initial deploy, run:
#   docker compose -f docker-compose.prod.yml exec iam pnpm seed:admin
CMD ["sh", "-c", "./node_modules/.bin/prisma migrate deploy --schema ./prisma/schema/schema.prisma && node server.js"]
