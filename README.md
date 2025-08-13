# 🎬 多語言音檔轉繁體中文字幕檔

使用 faster-whisper 和 Gradio 構建的語音轉字幕服務，支持多語言音頻自動轉錄並翻譯成繁體中文 SRT 字幕檔。

## 功能特色

- 🌍 支持 99+ 種語言自動偵測
- 🎯 高精度語音轉文字 (faster-whisper)
- 🇹🇼 自動翻譯為繁體中文
- 🎬 生成標準 SRT 字幕檔案
- 📝 支持雙語字幕 (原文+中文)
- 🖥️ 友善的 Web 介面 (Gradio)
- 📱 支持錄音和檔案上傳
- ⚡ 多種模型大小選擇
- ⏰ 自動時間戳同步

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

- **音頻輸入**: MP3, WAV, M4A, FLAC, OGG
- **語言**: 自動偵測 99+ 種語言
- **字幕輸出**: 
  - 繁體中文 SRT 字幕檔
  - 雙語 SRT 字幕檔 (原文+中文)

## 字幕檔案格式

生成的 SRT 檔案格式：
```
1
00:00:00,000 --> 00:00:03,500
這是第一句繁體中文字幕

2
00:00:03,500 --> 00:00:07,200
這是第二句繁體中文字幕
```

雙語字幕格式：
```
1
00:00:00,000 --> 00:00:03,500
Hello, this is the original text
這是繁體中文翻譯
```

## 模型選擇

- `tiny`: 最快，記憶體需求最小
- `base`: 平衡速度和準確度 (推薦)
- `small`: 更高準確度
- `medium`: 最高準確度，但較慢

## 使用流程

1. **上傳音頻檔案** - 支援多種格式，或直接錄音
2. **選擇模型大小** - 根據速度和準確度需求選擇
3. **選擇字幕類型** - 純中文或雙語字幕
4. **生成字幕** - 自動轉錄、翻譯並生成 SRT 檔案
5. **下載字幕檔** - 獲得可直接使用的字幕檔案

## 注意事項

- 首次使用需下載模型檔案
- 長音頻檔案處理時間較長
- 建議音頻品質越高越好
- 生成的 SRT 檔案可直接用於各種影片播放器
- 雙語字幕適合學習和對照使用