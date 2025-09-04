# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Copy only dependency files first for better caching
COPY pyproject.toml ./
COPY uv.lock ./

# Install uv first
RUN pip install --no-cache-dir uv

# Install Python dependencies
RUN uv pip install --system -e .

# Copy the entire app source
COPY . .

# Expose the application port
EXPOSE 8000

# Run the application using uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]