# 🎙️ 多語言語音轉繁體中文服務

使用 faster-whisper 和 Gradio 構建的語音轉錄翻譯服務，支持多語言音頻自動轉錄並翻譯成繁體中文。

## 功能特色

- 🌍 支持 99+ 種語言自動偵測
- 🎯 高精度語音轉文字 (faster-whisper)
- 🇹🇼 自動翻譯為繁體中文
- 🖥️ 友善的 Web 介面 (Gradio)
- 📱 支持錄音和檔案上傳
- ⚡ 多種模型大小選擇

## 安裝使用

### 本地運行

```bash
# 克隆項目
git clone <your-repo>
cd whisper-translator

# 安裝依賴
pip install -r requirements.txt

# 啟動服務
python app.py
```

服務將在 http://localhost:7860 啟動

### Docker 部署

```bash
# 構建映像
docker build -t whisper-translator .

# 運行容器
docker run -p 7860:7860 whisper-translator
```

## 部署選項

### Zeabur 部署 (推薦)

1. 將代碼推送到 GitHub
2. 在 Zeabur 創建新服務
3. 連接 GitHub 倉庫
4. 自動部署

### Google Colab

```python
!git clone <your-repo>
%cd whisper-translator
!pip install -r requirements.txt
!python app.py --share
```

## 支援格式

- **音頻**: MP3, WAV, M4A, FLAC, OGG
- **語言**: 自動偵測 99+ 種語言
- **輸出**: 繁體中文

## 模型選擇

- `tiny`: 最快，記憶體需求最小
- `base`: 平衡速度和準確度 (推薦)
- `small`: 更高準確度
- `medium`: 最高準確度，但較慢

## 注意事項

- 首次使用需下載模型檔案
- 長音頻檔案處理時間較長
- 建議音頻品質越高越好