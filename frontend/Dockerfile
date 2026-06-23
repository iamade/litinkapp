FROM node:20-alpine

WORKDIR /app
COPY package.json package-lock.json* yarn.lock* ./
RUN npm install --legacy-peer-deps
COPY . .

ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_API_URL=${VITE_API_URL}
ENV HOST=0.0.0.0
ENV PORT=5173
EXPOSE 5173

# Production build + static serve (Vite dev mode breaks staging hydration/tests)
RUN npm run build
CMD ["npx", "serve", "-s", "dist", "-l", "tcp://0.0.0.0:5173"]
