FROM python:3.10-slim

WORKDIR /app

# 複製檔案
COPY . /app

# 安裝所需套件
RUN pip install --no-cache-dir -r requirements.txt

# 服務啟動
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]


