import gradio as gr
import os
import tempfile
from faster_whisper import WhisperModel
from googletrans import Translator
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhisperTranslator:
    def __init__(self):
        # 初始化 Whisper 模型 (使用較小的模型以節省記憶體)
        self.whisper_model = None
        self.translator = Translator()
        
    def load_whisper_model(self, model_size="base"):
        """動態載入 Whisper 模型"""
        if self.whisper_model is None:
            logger.info(f"載入 Whisper 模型: {model_size}")
            self.whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
        return self.whisper_model
    
    def transcribe_audio(self, audio_file, model_size="base"):
        """轉錄音頻為文字"""
        try:
            if audio_file is None:
                return "請上傳音頻檔案", "", ""
            
            # 載入模型
            model = self.load_whisper_model(model_size)
            
            # 轉錄音頻
            logger.info("開始轉錄音頻...")
            segments, info = model.transcribe(audio_file, beam_size=5)
            
            # 提取文字
            transcribed_text = ""
            for segment in segments:
                transcribed_text += segment.text + " "
            
            transcribed_text = transcribed_text.strip()
            detected_language = info.language
            
            logger.info(f"轉錄完成，偵測語言: {detected_language}")
            
            if not transcribed_text:
                return "無法從音頻中提取文字", "", ""
            
            return transcribed_text, detected_language, ""
            
        except Exception as e:
            logger.error(f"轉錄錯誤: {str(e)}")
            return "", "", f"轉錄錯誤: {str(e)}"
    
    def translate_to_traditional_chinese(self, text):
        """翻譯為繁體中文"""
        try:
            if not text:
                return "沒有文字需要翻譯", ""
            
            logger.info("開始翻譯...")
            result = self.translator.translate(text, dest='zh-tw')
            translated_text = result.text
            
            logger.info("翻譯完成")
            return translated_text, ""
            
        except Exception as e:
            logger.error(f"翻譯錯誤: {str(e)}")
            return "", f"翻譯錯誤: {str(e)}"
    
    def process_audio(self, audio_file, model_size="base"):
        """完整處理流程：轉錄 + 翻譯"""
        # 步驟 1: 轉錄音頻
        transcribed_text, detected_language, transcribe_error = self.transcribe_audio(audio_file, model_size)
        
        if transcribe_error:
            return "", "", "", transcribe_error
        
        if not transcribed_text:
            return "", "", "", "無法從音頻中提取文字"
        
        # 步驟 2: 翻譯為繁體中文
        translated_text, translate_error = self.translate_to_traditional_chinese(transcribed_text)
        
        if translate_error:
            return transcribed_text, detected_language, "", translate_error
        
        return transcribed_text, detected_language, translated_text, ""

# 初始化翻譯器
translator = WhisperTranslator()

# 創建 Gradio 介面
def create_interface():
    with gr.Blocks(title="多語言語音轉繁體中文", theme=gr.themes.Soft()) as interface:
        gr.Markdown(
            """
            # 🎙️ 多語言語音轉繁體中文服務
            
            上傳任何語言的音頻檔案，自動轉錄並翻譯成繁體中文
            
            **支援格式**: MP3, WAV, M4A, FLAC 等
            **支援語言**: 99+ 種語言自動偵測
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
                
                # 處理按鈕
                process_btn = gr.Button("🚀 開始轉錄和翻譯", variant="primary")
            
            with gr.Column(scale=2):
                # 結果顯示
                with gr.Group():
                    gr.Markdown("### 📝 轉錄結果")
                    original_text = gr.Textbox(
                        label="原文",
                        placeholder="轉錄的原始文字將顯示在這裡...",
                        lines=4
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
                        lines=4
                    )
                
                # 錯誤訊息
                error_msg = gr.Textbox(
                    label="錯誤訊息",
                    visible=False
                )
        
        # 範例音頻（如果有的話）
        gr.Markdown("### 💡 使用說明")
        gr.Markdown(
            """
            1. **上傳音頻**: 點擊上方音頻區域上傳檔案，或使用麥克風錄音
            2. **選擇模型**: 根據需求選擇模型大小（建議使用 base）
            3. **開始處理**: 點擊按鈕開始轉錄和翻譯
            4. **查看結果**: 在右側查看轉錄原文和繁體中文翻譯
            
            **注意**: 首次使用時需要下載模型，可能需要幾分鐘時間
            """
        )
        
        # 處理函數
        def process_audio_wrapper(audio, model):
            try:
                original, language, translated, error = translator.process_audio(audio, model)
                
                if error:
                    return original, language, translated, gr.update(value=error, visible=True)
                else:
                    return original, language, translated, gr.update(visible=False)
                    
            except Exception as e:
                return "", "", "", gr.update(value=f"處理錯誤: {str(e)}", visible=True)
        
        # 綁定事件
        process_btn.click(
            fn=process_audio_wrapper,
            inputs=[audio_input, model_size],
            outputs=[original_text, detected_lang, translated_text, error_msg]
        )
    
    return interface

if __name__ == "__main__":
    # 創建並啟動介面
    interface = create_interface()
    
    # 從環境變數獲取配置
    server_name = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
    server_port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    
    interface.launch(
        server_name=server_name,
        server_port=server_port,
        share=False,
        debug=False  # 生產環境關閉 debug
    )