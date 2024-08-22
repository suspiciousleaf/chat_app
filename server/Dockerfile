FROM python:3.12

# Set working directory
WORKDIR /app

# Install vim-tiny and clean up apt cache to keep the image size small
RUN apt-get update && apt-get install -y vim-tiny && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY ./requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt
