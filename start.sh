#!/bin/bash

# 啟動健康檢查服務器（背景執行）
python health_endpoint.py &

# 等待一秒讓健康檢查服務器啟動
sleep 1

# 啟動 Streamlit 應用
exec streamlit run streamlit_app.py \
    --server.port=8080 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.runOnSave=false \
    --server.maxUploadSize=100