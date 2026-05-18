FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DATA_DIR=/app/data
ENV PORT=8501

RUN python updater.py --seed-demo
RUN chmod +x /app/start.sh

EXPOSE 8501

CMD ["/app/start.sh"]
