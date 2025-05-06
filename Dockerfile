
FROM python:3.10-slim


WORKDIR /app


COPY . /app


RUN pip install --no-cache-dir -r requirements.txt


RUN apt-get update && apt-get install -y openjdk-17-jdk git

ENV PYTHONPATH="/app/spotbugs1"

EXPOSE 5000

CMD ["gunicorn", "--timeout", "300", "-w", "4", "-b", "0.0.0.0:5000", "spotbugs1.app:app"]

