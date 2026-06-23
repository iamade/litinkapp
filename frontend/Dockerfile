FROM node:20-alpine

WORKDIR /app
COPY package.json package-lock.json* yarn.lock* ./
RUN npm install --legacy-peer-deps
COPY . .

ENV HOST=0.0.0.0
ENV PORT=5173
EXPOSE 5173

# Production build + static serve (Vite dev mode breaks staging hydration/tests)
RUN npm run build
CMD ["npx", "serve", "-s", "dist", "-l", "tcp://0.0.0.0:5173"]
