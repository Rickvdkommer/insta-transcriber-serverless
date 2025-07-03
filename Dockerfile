FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy all code
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the entrypoint
CMD ["python", "-u", "handler.py"] 