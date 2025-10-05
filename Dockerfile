# Stage 1: Build the application
FROM python:3.12-slim-buster AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --no-input

# Stage 2: Final image with Tailscale
FROM python:3.12-slim-buster

WORKDIR /app

# Copy built application from builder stage
COPY --from=builder /app .
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Install Tailscale
RUN apt-get update && apt-get install -y curl
RUN curl -fsSL https://pkgs.tailscale.com/stable/debian/buster.no-key.gpg | apt-key add -
RUN curl -fsSL https://pkgs.tailscale.com/stable/debian/buster.tailscale-key.asc | apt-key add -
RUN echo "deb https://pkgs.tailscale.com/stable/debian buster main" > /etc/apt/sources.list.d/tailscale.list
RUN apt-get update && apt-get install -y tailscale

# Copy the startup script
COPY start.sh .
RUN chmod +x ./start.sh

# Expose the port the app runs on
EXPOSE 8000

# Run the startup script
CMD ["./start.sh"]