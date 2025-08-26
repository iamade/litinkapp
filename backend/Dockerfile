FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install debugpy only for development
ARG ENVIRONMENT=production
RUN if [ "$ENVIRONMENT" = "development" ] ; then pip install debugpy ; fi


# Copy application code
COPY . .

# Copy and make entrypoint script executable
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Create uploads directory
RUN mkdir -p uploads/audio uploads/video

# Expose port
EXPOSE 8000

# Expose debug port
EXPOSE 5678

# # Run the application
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Use JSON format for proper signal handling
CMD ["./entrypoint.sh"]