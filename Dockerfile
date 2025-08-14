FROM python:3.9-slim

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# 升級 pip 並設置超時參數
RUN pip install --upgrade pip

# 設置工作目錄
WORKDIR /app

# 複製依賴文件
COPY requirements.txt .

# 安裝 Python 依賴 (添加重試和超時配置)
RUN pip install --no-cache-dir \
    --timeout 300 \
    --retries 3 \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    -r requirements.txt

# 複製應用代碼
COPY . .

# 運行健康檢查
RUN python health_check.py

# 暴露端口
EXPOSE 8080

# 啟動命令
CMD ["python", "app.py"]