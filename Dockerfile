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

# Install necessary dependencies for adding a new repository, including gnupg
RUN apt-get update && apt-get install -y curl gnupg

# Add Tailscale's official GPG key to the keyring
RUN curl -fsSL https://pkgs.tailscale.com/stable/debian/bookworm.no-key.gpg | gpg --dearmor -o /usr/share/keyrings/tailscale-archive-keyring.gpg

# Add the Tailscale repository to the system's sources list
RUN echo "deb [signed-by=/usr/share/keyrings/tailscale-archive-keyring.gpg] https://pkgs.tailscale.com/stable/debian bookworm main" > /etc/apt/sources.list.d/tailscale.list

# Update package list and install Tailscale
RUN apt-get update && apt-get install -y tailscale

# Copy the startup script
COPY start.sh .
RUN chmod +x ./start.sh

# Expose the port the app runs on
EXPOSE 8000

# Run the startup script
CMD ["./start.sh"]