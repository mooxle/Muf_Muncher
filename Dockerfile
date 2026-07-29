FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends cron \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY muf.py dashboard_template.html mufmuncher-icon.png mufmuncher-llama.png mufmuncher-wave.png muf.css ./

COPY muf-cron /etc/cron.d/muf-cron
RUN chmod 0644 /etc/cron.d/muf-cron

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /data
VOLUME /data

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
