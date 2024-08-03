# Base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libnss3-dev \
    libxss1 \
    libasound2 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    tk \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    dpkg -i google-chrome-stable_current_amd64.deb; apt-get -fy install && \
    rm google-chrome-stable_current_amd64.deb

# Install ChromeDriver
RUN CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
    wget -q https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip && \
    mv chromedriver /usr/local/bin/ && \
    rm chromedriver_linux64.zip

# Install virtualenv
RUN pip install virtualenv

# Create a virtual environment
RUN python -m virtualenv /app/.venv

# Set the working directory
WORKDIR /app

# Copy the application code
COPY . /app

# Activate the virtual environment and install dependencies
RUN /app/.venv/bin/pip install \
    numpy \
    pandas \
    openpyxl \
    Pillow \
    scikit-image \
    opencv-python-headless \
    selenium \
    webdriver-manager \
    configparser \
    tk

# Expose the port
EXPOSE 5000

# Set entrypoint to the python script, allowing it to accept command-line arguments
ENTRYPOINT ["/app/.venv/bin/python", "test_app.py"]
