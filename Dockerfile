# Stage 1: Build the application
FROM python:3.12-slim-bookworm AS builder

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
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy built application from builder stage
COPY --from=builder /app .
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

RUN curl -fsSL https://tailscale.com/install.sh | sh

# Copy the startup script
COPY start.sh .
RUN chmod +x ./start.sh

# Expose the port the app runs on
EXPOSE 8000

# Run the startup script
CMD ["./start.sh"]