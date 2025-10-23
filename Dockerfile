FROM python:3.12

ENV REDIS_URL=redis://redis PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

# Create data directory for databases
RUN mkdir -p /app/data

# Expose the backend port 8000
EXPOSE 8000

# Run the backend ONLY
CMD ["reflex", "run", "--env", "prod", "--backend-only", "--backend-host", "0.0.0.0", "--backend-port", "8000", "--loglevel", "debug"]