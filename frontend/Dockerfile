# Frontend Dockerfile for Doc Translation System

# Build stage
FROM node:22-alpine AS builder

# Set work directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including devDependencies for build)
RUN npm ci

# Copy source code
COPY . .

# Allow overriding API URL at build time (relative path for ECS(ALB) deployments)
ARG VITE_API_URL=/api/graphql
ENV VITE_API_URL=${VITE_API_URL}

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Install curl and wget
RUN apk add --no-cache curl wget

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built application from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Create non-root user for security
RUN addgroup -g 1001 -S appuser && \
    adduser -S appuser -G appuser -u 1001

# Create directories for nginx to run as non-root and set permissions
RUN mkdir -p /var/run/nginx && \
    chown -R appuser:appuser /usr/share/nginx/html && \
    chown -R appuser:appuser /var/cache/nginx && \
    chown -R appuser:appuser /var/log/nginx && \
    chown -R appuser:appuser /var/run/nginx && \
    chown -R appuser:appuser /etc/nginx/conf.d && \
    touch /var/run/nginx/nginx.pid && \
    chown appuser:appuser /var/run/nginx/nginx.pid

# Update nginx.conf to use the new pid location
RUN sed -i 's|pid\s*/run/nginx.pid;|pid /var/run/nginx/nginx.pid;|' /etc/nginx/nginx.conf && \
    sed -i 's|user\s*nginx;|#user nginx;|' /etc/nginx/nginx.conf

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]