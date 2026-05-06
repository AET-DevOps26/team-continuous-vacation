# Stage 1: Build the React application
FROM node:20-alpine AS builder
WORKDIR /app

# Copy package.json (but NOT the lockfile or node_modules)
COPY package.json ./

RUN npm install --legacy-peer-deps

# Copy the rest of the source code
COPY . .

# Build the Vite app
RUN npm run build

# Stage 2: Serve the application
FROM node:20-alpine AS runner
WORKDIR /app

# Install the static server
RUN npm install -g serve

# Copy only the compiled output from the builder stage
COPY --from=builder /app/dist ./dist

EXPOSE 3000

# Serve the SPA and redirect all routes to index.html (-s)
CMD ["serve", "-s", "dist", "-l", "3000"]
