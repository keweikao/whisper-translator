#!/usr/bin/env python3
"""
簡單的健康檢查端點，用於 Zeabur 健康檢查
"""
import http.server
import socketserver
import json
import threading
import time
from datetime import datetime

class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "whisper-translator"
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # 靜默健康檢查日誌
        return

def start_health_server():
    """在背景啟動健康檢查服務器"""
    try:
        PORT = 8081
        with socketserver.TCPServer(("", PORT), HealthHandler) as httpd:
            print(f"健康檢查服務器啟動於端口 {PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"健康檢查服務器啟動失敗: {e}")

if __name__ == "__main__":
    # 在背景執行緒中啟動健康檢查服務器
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # 保持主執行緒運行
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("健康檢查服務器關閉")