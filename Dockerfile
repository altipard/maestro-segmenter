FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .
COPY *.pyi .

EXPOSE 50051

CMD ["python", "main.py"]
