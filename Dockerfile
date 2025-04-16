# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Java for SpotBugs, PMD, etc.
RUN apt-get update && apt-get install -y openjdk-17-jdk git

# Tell Python where your project root is
ENV PYTHONPATH="/app/spotbugs1"

EXPOSE 5000

CMD ["gunicorn", "--timeout", "300", "-w", "4", "-b", "0.0.0.0:5000", "spotbugs1.app:app"]

