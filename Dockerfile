FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir sentence-transformers faiss-cpu fastapi uvicorn
EXPOSE 8000
CMD ["python", "api/main.py"]