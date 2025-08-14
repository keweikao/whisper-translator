#!/usr/bin/env python3
"""
FastAPI 版本的多語言音檔轉繁體中文字幕服務
"""
import os
import tempfile
import logging
from pathlib import Path
from typing import Optional

import whisper
from deep_translator import GoogleTranslator
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from datetime import timedelta
import re
import uuid

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 創建 FastAPI 應用
app = FastAPI(title="多語言音檔轉繁體中文字幕檔", version="1.0.0")

# 設置模板
templates = Jinja2Templates(directory="templates")

# 創建臨時文件目錄
TEMP_DIR = Path("temp_files")
TEMP_DIR.mkdir(exist_ok=True)

class WhisperSubtitleTranslator:
    def __init__(self):
        self.whisper_model = None
        self.translator = GoogleTranslator(source='auto', target='zh-TW')
        
    def load_whisper_model(self, model_size="base"):
        """動態載入 Whisper 模型"""
        if self.whisper_model is None:
            logger.info(f"載入 Whisper 模型: {model_size}")
            self.whisper_model = whisper.load_model(model_size)
        return self.whisper_model
    
    def format_timestamp(self, seconds):
        """將秒數轉換為 SRT 時間格式 (HH:MM:SS,mmm)"""
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{milliseconds:03d}"
    
    def clean_text_for_subtitle(self, text):
        """清理文字以適合字幕顯示"""
        text = re.sub(r'\s+', ' ', text.strip())
        if len(text) > 40:
            words = text.split(' ')
            lines = []
            current_line = ""
            for word in words:
                if len(current_line + " " + word) <= 40:
                    current_line += (" " + word if current_line else word)
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            text = "\n".join(lines)
        return text
    
    def transcribe_with_timestamps(self, audio_file, model_size="base"):
        """轉錄音頻並保留時間戳"""
        try:
            model = self.load_whisper_model(model_size)
            logger.info("開始轉錄音頻...")
            result = model.transcribe(audio_file)
            
            segments_data = []
            for segment in result["segments"]:
                segments_data.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'].strip()
                })
            
            detected_language = result["language"]
            logger.info(f"轉錄完成，偵測語言: {detected_language}，共 {len(segments_data)} 個片段")
            
            return segments_data, detected_language, ""
            
        except Exception as e:
            logger.error(f"轉錄錯誤: {str(e)}")
            return [], "", f"轉錄錯誤: {str(e)}"
    
    def translate_to_traditional_chinese(self, text):
        """翻譯為繁體中文"""
        try:
            if not text:
                return "沒有文字需要翻譯", ""
            
            logger.info("開始翻譯...")
            translated_text = self.translator.translate(text)
            
            if translated_text is None:
                translated_text = ""
            elif not isinstance(translated_text, str):
                translated_text = str(translated_text)
            
            logger.info("翻譯完成")
            return translated_text, ""
            
        except Exception as e:
            logger.error(f"翻譯錯誤: {str(e)}")
            return "", str(e)
    
    def generate_srt_content(self, segments_data, translated_segments):
        """生成 SRT 字幕檔內容"""
        srt_content = ""
        
        for i, (original_seg, translated_text) in enumerate(zip(segments_data, translated_segments), 1):
            start_time = self.format_timestamp(original_seg['start'])
            end_time = self.format_timestamp(original_seg['end'])
            
            clean_translated = self.clean_text_for_subtitle(translated_text)
            
            srt_content += f"{i}\n"
            srt_content += f"{start_time} --> {end_time}\n"
            srt_content += f"{clean_translated}\n\n"
        
        return srt_content
    
    def process_audio_to_srt(self, audio_file, model_size="base", include_original=False):
        """完整處理流程：轉錄 + 翻譯 + 生成 SRT"""
        # 步驟 1: 轉錄音頻
        segments_data, detected_language, transcribe_error = self.transcribe_with_timestamps(audio_file, model_size)
        
        if transcribe_error:
            raise Exception(f"轉錄錯誤: {transcribe_error}")
        
        if not segments_data:
            raise Exception("無法從音頻中提取文字")
        
        # 步驟 2: 翻譯每個片段
        logger.info("開始翻譯片段...")
        translated_segments = []
        original_texts = []
        
        for segment in segments_data:
            original_text = segment['text']
            original_texts.append(original_text)
            
            translated_text, translate_error = self.translate_to_traditional_chinese(original_text)
            if translate_error:
                raise Exception(f"翻譯錯誤: {translate_error}")
            
            translated_segments.append(translated_text)
        
        # 步驟 3: 生成 SRT 檔案
        srt_content = self.generate_srt_content(segments_data, translated_segments)
        
        result = {
            'original_texts': original_texts,
            'detected_language': detected_language,
            'translated_segments': translated_segments,
            'srt_content': srt_content,
            'segments_count': len(segments_data)
        }
        
        # 如果需要雙語字幕
        if include_original:
            bilingual_srt = ""
            for i, (original_seg, original_text, translated_text) in enumerate(zip(segments_data, original_texts, translated_segments), 1):
                start_time = self.format_timestamp(original_seg['start'])
                end_time = self.format_timestamp(original_seg['end'])
                
                clean_original = self.clean_text_for_subtitle(original_text)
                clean_translated = self.clean_text_for_subtitle(translated_text)
                
                bilingual_srt += f"{i}\n"
                bilingual_srt += f"{start_time} --> {end_time}\n"
                bilingual_srt += f"{clean_original}\n{clean_translated}\n\n"
            
            result['bilingual_srt'] = bilingual_srt
        
        return result

# 初始化翻譯器
translator = WhisperSubtitleTranslator()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """首頁"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/process")
async def process_audio(
    audio: UploadFile = File(...),
    model: str = Form("base"),
    bilingual: Optional[str] = Form(None)
):
    """處理音頻檔案並生成字幕"""
    try:
        # 驗證檔案格式
        if not audio.filename.lower().endswith(('.mp3', '.wav', '.m4a', '.flac', '.ogg')):
            raise HTTPException(status_code=400, detail="不支援的音頻格式")
        
        # 保存上傳的檔案
        file_id = str(uuid.uuid4())
        temp_audio_path = TEMP_DIR / f"{file_id}_{audio.filename}"
        
        with open(temp_audio_path, "wb") as buffer:
            content = await audio.read()
            buffer.write(content)
        
        logger.info(f"處理音頻檔案: {audio.filename}, 模型: {model}")
        
        # 處理音頻
        include_original = bilingual == "true"
        result = translator.process_audio_to_srt(
            str(temp_audio_path), 
            model_size=model, 
            include_original=include_original
        )
        
        # 保存 SRT 檔案
        srt_filename = f"{file_id}_subtitle.srt"
        srt_path = TEMP_DIR / srt_filename
        
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(result['srt_content'])
        
        response_data = {
            "success": True,
            "language": result['detected_language'],
            "segments_count": result['segments_count'],
            "original_text": "\n".join(result['original_texts'][:5]) + ("..." if len(result['original_texts']) > 5 else ""),
            "translated_text": "\n".join(result['translated_segments'][:5]) + ("..." if len(result['translated_segments']) > 5 else ""),
            "srt_filename": srt_filename
        }
        
        # 如果是雙語字幕
        if include_original and 'bilingual_srt' in result:
            bilingual_filename = f"{file_id}_bilingual.srt"
            bilingual_path = TEMP_DIR / bilingual_filename
            
            with open(bilingual_path, "w", encoding="utf-8") as f:
                f.write(result['bilingual_srt'])
            
            response_data['bilingual_filename'] = bilingual_filename
        
        # 清理臨時音頻檔案
        temp_audio_path.unlink()
        
        return response_data
        
    except Exception as e:
        logger.error(f"處理錯誤: {str(e)}")
        # 清理可能的臨時檔案
        if 'temp_audio_path' in locals() and temp_audio_path.exists():
            temp_audio_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{filename}")
async def download_file(filename: str):
    """下載字幕檔案"""
    file_path = TEMP_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="檔案不存在")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='text/plain; charset=utf-8'
    )

@app.get("/health")
async def health_check():
    """健康檢查"""
    return {"status": "healthy", "service": "whisper-subtitle-translator"}

if __name__ == "__main__":
    import uvicorn
    
    # 從環境變數獲取配置
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    
    logger.info(f"啟動服務於 {host}:{port}")
    
    uvicorn.run(app, host=host, port=port)