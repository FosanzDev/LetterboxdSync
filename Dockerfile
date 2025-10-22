FROM python:3.12

# Install Node.js and unzip (required for Reflex)
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

ENV REDIS_URL=redis://redis PYTHONUNBUFFERED=1

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

# Create data directory for databases
RUN mkdir -p /app/data

# Initialize the web directory and install frontend dependencies
RUN reflex init

# Run the full app (both frontend and backend)
CMD ["reflex", "run", "--env", "prod", "--loglevel", "debug"]