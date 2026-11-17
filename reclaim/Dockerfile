# Container image for hosts with persistent disks (e.g. Fly.io Toronto, a Canadian VPS).
FROM node:22-bookworm-slim
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build
ENV NODE_ENV=production RECLAIM_DATA_DIR=/data PORT=3000
EXPOSE 3000
# SITE_PASSWORD must be set at run time (e.g. fly secrets set SITE_PASSWORD=...).
CMD ["npm", "start"]
