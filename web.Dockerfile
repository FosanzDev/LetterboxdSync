# --- Builder Stage ---
FROM python:3.12 AS builder

# 1. Install Node.js and unzip
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Set the public API_URL for the static export
ENV API_URL="https://lbsync.fosanz.dev"

RUN pip install -r requirements.txt
RUN reflex init
RUN reflex export --frontend-only --no-zip

# --- DEBUGGING STEP (Optional) ---
RUN ls -laR /app/.web

# --- Final image ---
FROM nginx
# **CRITICAL FIX**: Copy the built static files from the new 'build/client' directory
COPY --from=builder /app/.web/build/client /usr/share/nginx/html
# Copy the Nginx config
COPY ./nginx.conf /etc/nginx/conf.d/default.conf