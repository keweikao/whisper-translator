import gradio as gr
import os
import tempfile
import whisper
from deep_translator import GoogleTranslator
import logging
from datetime import timedelta
import re

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 確保使用 OpenAI Whisper 而非 faster-whisper

class WhisperSubtitleTranslator:
    def __init__(self):
        # 初始化 Whisper 模型 (使用較小的模型以節省記憶體)
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
        # 移除多餘的空格和換行
        text = re.sub(r'\s+', ' ', text.strip())
        # 限制每行長度 (建議 35-40 字元)
        if len(text) > 40:
            # 簡單的斷行處理
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
            if audio_file is None:
                return [], "", ""
            
            # 載入模型
            model = self.load_whisper_model(model_size)
            
            # 轉錄音頻並保留時間戳
            logger.info("開始轉錄音頻...")
            result = model.transcribe(audio_file)
            
            # 提取分段信息
            segments_data = []
            for segment in result["segments"]:
                segments_data.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'].strip()
                })
            
            detected_language = result["language"]
            logger.info(f"轉錄完成，偵測語言: {detected_language}，共 {len(segments_data)} 個片段")
            
            if not segments_data:
                return [], "", "無法從音頻中提取文字"
            
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
            
            logger.info("翻譯完成")
            return translated_text, ""
            
        except Exception as e:
            logger.error(f"翻譯錯誤: {str(e)}")
            return "", f"翻譯錯誤: {str(e)}"
    
    def generate_srt_content(self, segments_data, translated_segments):
        """生成 SRT 字幕檔內容"""
        srt_content = ""
        
        for i, (original_seg, translated_text) in enumerate(zip(segments_data, translated_segments), 1):
            start_time = self.format_timestamp(original_seg['start'])
            end_time = self.format_timestamp(original_seg['end'])
            
            # 清理翻譯文字以適合字幕
            clean_translated = self.clean_text_for_subtitle(translated_text)
            
            srt_content += f"{i}\n"
            srt_content += f"{start_time} --> {end_time}\n"
            srt_content += f"{clean_translated}\n\n"
        
        return srt_content
    
    def process_audio_to_srt(self, audio_file, model_size="base", include_original=False):
        """完整處理流程：轉錄 + 翻譯 + 生成 SRT"""
        # 步驟 1: 轉錄音頻並獲取時間戳
        segments_data, detected_language, transcribe_error = self.transcribe_with_timestamps(audio_file, model_size)
        
        if transcribe_error:
            return "", "", "", "", "", transcribe_error
        
        if not segments_data:
            return "", "", "", "", "", "無法從音頻中提取文字"
        
        # 步驟 2: 翻譯每個片段
        logger.info("開始翻譯片段...")
        translated_segments = []
        original_texts = []
        
        for segment in segments_data:
            original_text = segment['text']
            original_texts.append(original_text)
            
            # 翻譯片段
            translated_text, translate_error = self.translate_to_traditional_chinese(original_text)
            if translate_error:
                return "", "", "", "", "", f"翻譯錯誤: {translate_error}"
            
            translated_segments.append(translated_text)
        
        # 步驟 3: 生成 SRT 檔案
        srt_content = self.generate_srt_content(segments_data, translated_segments)
        
        # 如果需要包含原文，生成雙語 SRT
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
            
            return "\n".join(original_texts), detected_language, "\n".join(translated_segments), srt_content, bilingual_srt, ""
        
        return "\n".join(original_texts), detected_language, "\n".join(translated_segments), srt_content, "", ""

# 初始化翻譯器
translator = WhisperSubtitleTranslator()

# 創建 Gradio 介面
def create_interface():
    with gr.Blocks(title="多語言音檔轉繁中字幕", theme=gr.themes.Soft()) as interface:
        gr.Markdown(
            """
            # 🎬 多語言音檔轉繁體中文字幕檔
            
            上傳任何語言的音頻檔案，自動轉錄並翻譯成繁體中文 SRT 字幕檔
            
            **支援格式**: MP3, WAV, M4A, FLAC 等音頻檔案
            **支援語言**: 99+ 種語言自動偵測
            **輸出格式**: 標準 SRT 字幕檔案
            """
        )
        
        with gr.Row():
            with gr.Column(scale=1):
                # 音頻輸入
                audio_input = gr.Audio(
                    label="上傳音頻檔案或錄音",
                    type="filepath"
                )
                
                # 模型選擇
                model_size = gr.Dropdown(
                    choices=["tiny", "base", "small", "medium"],
                    value="base",
                    label="模型大小 (影響速度和準確度)",
                    info="tiny: 最快但準確度較低 | base: 平衡 | small/medium: 較慢但更準確"
                )
                
                # 雙語字幕選項
                include_original = gr.Checkbox(
                    label="生成雙語字幕",
                    value=False,
                    info="勾選後會生成包含原文和中文的雙語字幕檔"
                )
                
                # 處理按鈕
                process_btn = gr.Button("🎬 生成繁中字幕檔", variant="primary")
            
            with gr.Column(scale=2):
                # 結果顯示
                with gr.Group():
                    gr.Markdown("### 📝 轉錄結果")
                    original_text = gr.Textbox(
                        label="原文內容",
                        placeholder="轉錄的原始文字將顯示在這裡...",
                        lines=3
                    )
                    
                    detected_lang = gr.Textbox(
                        label="偵測語言",
                        placeholder="自動偵測的語言將顯示在這裡..."
                    )
                
                with gr.Group():
                    gr.Markdown("### 🇹🇼 繁體中文翻譯")
                    translated_text = gr.Textbox(
                        label="繁體中文翻譯",
                        placeholder="翻譯結果將顯示在這裡...",
                        lines=3
                    )
                
                with gr.Group():
                    gr.Markdown("### 📥 字幕檔下載")
                    srt_file = gr.File(
                        label="繁體中文字幕檔 (.srt)",
                        visible=False
                    )
                    
                    bilingual_srt_file = gr.File(
                        label="雙語字幕檔 (.srt)",
                        visible=False
                    )
                
                # 錯誤訊息
                error_msg = gr.Textbox(
                    label="錯誤訊息",
                    visible=False
                )
        
        # 使用說明
        gr.Markdown("### 💡 使用說明")
        gr.Markdown(
            """
            1. **上傳音頻**: 點擊上方音頻區域上傳檔案，或使用麥克風錄音
            2. **選擇模型**: 根據需求選擇模型大小（建議使用 base）
            3. **雙語選項**: 勾選後會生成包含原文+中文的雙語字幕檔
            4. **生成字幕**: 點擊按鈕開始處理
            5. **下載字幕**: 處理完成後可下載 SRT 字幕檔
            
            **字幕格式**: 標準 SRT 格式，包含時間戳和文字，可直接用於視頻播放器
            **注意**: 首次使用時需要下載模型，可能需要幾分鐘時間
            """
        )
        
        # 處理函數
        def process_audio_wrapper(audio, model, include_bilingual):
            try:
                # 確保參數類型正確
                if audio is None:
                    return ("", "", "", 
                           gr.update(visible=False), gr.update(visible=False),
                           gr.update(value="請上傳音頻檔案", visible=True))
                
                # 確保 include_bilingual 是布林值
                include_bilingual = bool(include_bilingual)
                
                if include_bilingual:
                    original, language, translated, srt_content, bilingual_content, error = translator.process_audio_to_srt(audio, model, include_original=True)
                    
                    if error:
                        return (original, language, translated, 
                               gr.update(visible=False), gr.update(visible=False),
                               gr.update(value=error, visible=True))
                    
                    # 創建臨時檔案
                    import tempfile
                    
                    # 繁中字幕檔
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
                        f.write(srt_content)
                        srt_path = f.name
                    
                    # 雙語字幕檔
                    with tempfile.NamedTemporaryFile(mode='w', suffix='_bilingual.srt', delete=False, encoding='utf-8') as f:
                        f.write(bilingual_content)
                        bilingual_path = f.name
                    
                    return (original, language, translated,
                           gr.update(value=srt_path, visible=True),
                           gr.update(value=bilingual_path, visible=True),
                           gr.update(visible=False))
                
                else:
                    original, language, translated, srt_content, error = translator.process_audio_to_srt(audio, model, include_original=False)
                    
                    if error:
                        return (original, language, translated,
                               gr.update(visible=False), gr.update(visible=False),
                               gr.update(value=error, visible=True))
                    
                    # 創建繁中字幕檔
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
                        f.write(srt_content)
                        srt_path = f.name
                    
                    return (original, language, translated,
                           gr.update(value=srt_path, visible=True),
                           gr.update(visible=False),
                           gr.update(visible=False))
                    
            except Exception as e:
                return ("", "", "",
                       gr.update(visible=False), gr.update(visible=False),
                       gr.update(value=f"處理錯誤: {str(e)}", visible=True))
        
        # 綁定事件
        process_btn.click(
            fn=process_audio_wrapper,
            inputs=[audio_input, model_size, include_original],
            outputs=[original_text, detected_lang, translated_text, srt_file, bilingual_srt_file, error_msg]
        )
    
    return interface

if __name__ == "__main__":
    try:
        logger.info("正在啟動字幕生成服務...")
        
        # 創建並啟動介面
        interface = create_interface()
        
        # 從環境變數獲取配置
        server_name = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
        server_port = int(os.getenv("GRADIO_SERVER_PORT", "8080"))
        
        logger.info(f"啟動服務於 {server_name}:{server_port}")
        
        interface.launch(
            server_name=server_name,
            server_port=server_port,
            share=True
        )
        
    except Exception as e:
        logger.error(f"啟動失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        raise