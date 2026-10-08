FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY qicetong ./qicetong
COPY data ./data
COPY web ./web
ENV QCT_RUNTIME=/app/runtime
CMD ["python", "-m", "uvicorn", "qicetong.app:app", "--host", "0.0.0.0", "--port", "8765"]
