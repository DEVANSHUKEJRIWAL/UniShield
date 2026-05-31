FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
# npm ci fails on Alpine when lockfile was generated on macOS (optional @emnapi peers).
RUN npm install --omit=optional --no-audit --no-fund
COPY . .
RUN mkdir -p public
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
CMD ["node", "server.js"]
