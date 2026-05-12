FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ai_agent.py .

EXPOSE 5000

CMD ["python", "ai_agent.py"]
