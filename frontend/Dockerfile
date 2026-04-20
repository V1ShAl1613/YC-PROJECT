FROM node:20-alpine AS base
WORKDIR /app
COPY package*.json ./
RUN npm install

FROM base AS builder
COPY . .
RUN npm run build

FROM base AS runner
ENV NODE_ENV=production
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["npm", "start"]
