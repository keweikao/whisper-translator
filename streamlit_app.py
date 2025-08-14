#!/usr/bin/env python3
"""
Streamlit 版本的多語言音檔轉繁體中文字幕服務
"""
import streamlit as st
import tempfile
import logging
from pathlib import Path
from datetime import timedelta
import re
import whisper
from deep_translator import GoogleTranslator

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 頁面配置
st.set_page_config(
    page_title="🎬 多語言音檔轉繁中字幕",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

class WhisperSubtitleTranslator:
    def __init__(self):
        self.whisper_model = None
        self.translator = GoogleTranslator(source='auto', target='zh-TW')
        
    @st.cache_resource
    def load_whisper_model(_self, model_size="base"):
        """動態載入 Whisper 模型（使用 Streamlit 緩存）"""
        logger.info(f"載入 Whisper 模型: {model_size}")
        return whisper.load_model(model_size)
    
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
            
            with st.status("🎤 正在轉錄音頻...", expanded=True) as status:
                st.write("載入 Whisper 模型...")
                
                # 加入音頻預處理和錯誤處理
                transcribe_options = {
                    "fp16": False,  # 強制使用 FP32 避免張量問題
                    "verbose": False,
                    "condition_on_previous_text": False,  # 避免長音頻的累積錯誤
                }
                
                result = model.transcribe(audio_file, **transcribe_options)
                st.write("提取語音片段...")
                
                segments_data = []
                for segment in result["segments"]:
                    # 過濾掉過短或無效的片段
                    if segment.get('text', '').strip() and (segment['end'] - segment['start']) > 0.1:
                        segments_data.append({
                            'start': segment['start'],
                            'end': segment['end'],
                            'text': segment['text'].strip()
                        })
                
                detected_language = result["language"]
                st.write(f"✅ 轉錄完成！偵測語言: {detected_language}")
                status.update(label="✅ 轉錄完成", state="complete")
            
            logger.info(f"轉錄完成，偵測語言: {detected_language}，共 {len(segments_data)} 個片段")
            return segments_data, detected_language, ""
            
        except Exception as e:
            logger.error(f"轉錄錯誤: {str(e)}")
            
            # 嘗試使用更小的模型重試
            if model_size != "tiny":
                logger.info("嘗試使用 tiny 模型重試...")
                try:
                    return self.transcribe_with_timestamps(audio_file, "tiny")
                except:
                    pass
                    
            return [], "", f"轉錄錯誤: {str(e)}"
    
    def translate_to_traditional_chinese(self, text):
        """翻譯為繁體中文"""
        try:
            if not text:
                return "沒有文字需要翻譯", ""
            
            translated_text = self.translator.translate(text)
            
            if translated_text is None:
                translated_text = ""
            elif not isinstance(translated_text, str):
                translated_text = str(translated_text)
            
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
        with st.status("🌏 正在翻譯為繁體中文...", expanded=True) as status:
            translated_segments = []
            original_texts = []
            
            progress_bar = st.progress(0)
            total_segments = len(segments_data)
            
            for i, segment in enumerate(segments_data):
                original_text = segment['text']
                original_texts.append(original_text)
                
                translated_text, translate_error = self.translate_to_traditional_chinese(original_text)
                if translate_error:
                    raise Exception(f"翻譯錯誤: {translate_error}")
                
                translated_segments.append(translated_text)
                progress_bar.progress((i + 1) / total_segments)
                
            st.write("✅ 翻譯完成！")
            status.update(label="✅ 翻譯完成", state="complete")
        
        # 步驟 3: 生成 SRT 檔案
        with st.status("📝 生成字幕檔案...", expanded=True) as status:
            srt_content = self.generate_srt_content(segments_data, translated_segments)
            st.write("✅ SRT 字幕檔生成完成！")
            
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
                st.write("✅ 雙語字幕檔生成完成！")
            
            status.update(label="✅ 字幕檔生成完成", state="complete")
        
        return result

# 初始化翻譯器
@st.cache_resource
def get_translator():
    return WhisperSubtitleTranslator()

def main():
    """主應用"""
    st.title("🎬 多語言音檔轉繁體中文字幕檔")
    st.markdown("---")
    
    # 側邊欄設定
    with st.sidebar:
        st.header("⚙️ 設定選項")
        
        # 模型選擇
        model_size = st.selectbox(
            "🤖 選擇 Whisper 模型",
            ["tiny", "base", "small", "medium"],
            index=1,
            help="tiny: 最快但準確度較低 | base: 平衡（推薦）| small/medium: 較慢但更準確"
        )
        
        # 雙語字幕選項
        include_bilingual = st.checkbox(
            "📝 生成雙語字幕",
            help="勾選後會生成包含原文和中文的雙語字幕檔"
        )
        
        st.markdown("---")
        st.markdown("""
        ### 💡 功能特色
        - 🌍 支持 99+ 種語言自動偵測
        - 🎯 OpenAI Whisper 高精度轉錄
        - 🇹🇼 自動翻譯為繁體中文
        - 📋 生成標準 SRT 字幕檔
        - ⚡ 多種模型大小可選
        """)
    
    # 主要內容區域
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 上傳音頻檔案")
        
        # 檔案上傳
        uploaded_file = st.file_uploader(
            "選擇音頻檔案",
            type=['mp3', 'wav', 'm4a', 'flac', 'ogg'],
            help="支援格式：MP3, WAV, M4A, FLAC, OGG"
        )
        
        if uploaded_file is not None:
            st.success(f"✅ 已選擇檔案: {uploaded_file.name}")
            
            # 顯示檔案資訊
            file_size = len(uploaded_file.read())
            uploaded_file.seek(0)  # 重置檔案指針
            st.info(f"檔案大小: {file_size / 1024 / 1024:.2f} MB")
            
            # 處理按鈕
            if st.button("🚀 開始生成字幕", type="primary", use_container_width=True):
                try:
                    translator = get_translator()
                    
                    # 保存臨時檔案
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{uploaded_file.name}") as temp_file:
                        temp_file.write(uploaded_file.read())
                        temp_file_path = temp_file.name
                    
                    # 處理音頻
                    result = translator.process_audio_to_srt(
                        temp_file_path, 
                        model_size=model_size,
                        include_original=include_bilingual
                    )
                    
                    # 顯示結果
                    st.success("🎉 字幕生成完成！")
                    
                    # 結果資訊
                    col_info1, col_info2, col_info3 = st.columns(3)
                    with col_info1:
                        st.metric("偵測語言", result['detected_language'])
                    with col_info2:
                        st.metric("字幕片段", result['segments_count'])
                    with col_info3:
                        st.metric("處理狀態", "✅ 完成")
                    
                    # 下載區域
                    st.markdown("### 📥 下載字幕檔案")
                    
                    col_dl1, col_dl2 = st.columns(2)
                    
                    with col_dl1:
                        # 繁體中文字幕下載
                        # 清理檔案名稱，移除副檔名和特殊字符
                        clean_filename = uploaded_file.name.rsplit('.', 1)[0]
                        clean_filename = re.sub(r'[^\w\s-]', '', clean_filename)
                        
                        st.download_button(
                            label="📥 下載繁體中文字幕 (.srt)",
                            data=result['srt_content'].encode('utf-8'),
                            file_name=f"{clean_filename}_chinese_subtitle.srt",
                            mime="text/plain; charset=utf-8",
                            type="primary"
                        )
                    
                    with col_dl2:
                        # 雙語字幕下載
                        if include_bilingual and 'bilingual_srt' in result:
                            clean_filename = uploaded_file.name.rsplit('.', 1)[0]
                            clean_filename = re.sub(r'[^\w\s-]', '', clean_filename)
                            
                            st.download_button(
                                label="📥 下載雙語字幕 (.srt)",
                                data=result['bilingual_srt'].encode('utf-8'),
                                file_name=f"{clean_filename}_bilingual_subtitle.srt",
                                mime="text/plain; charset=utf-8",
                                type="secondary"
                            )
                    
                    # 預覽內容
                    with st.expander("📝 預覽轉錄內容", expanded=False):
                        tab1, tab2 = st.tabs(["原文", "繁體中文"])
                        
                        with tab1:
                            st.text_area(
                                "原文內容", 
                                "\n".join(result['original_texts'][:10]) + ("..." if len(result['original_texts']) > 10 else ""),
                                height=200
                            )
                        
                        with tab2:
                            st.text_area(
                                "繁體中文翻譯", 
                                "\n".join(result['translated_segments'][:10]) + ("..." if len(result['translated_segments']) > 10 else ""),
                                height=200
                            )
                    
                    # 清理臨時檔案
                    Path(temp_file_path).unlink()
                    
                except Exception as e:
                    st.error(f"❌ 處理失敗: {str(e)}")
                    logger.error(f"處理錯誤: {str(e)}")
                    if 'temp_file_path' in locals():
                        try:
                            Path(temp_file_path).unlink()
                        except:
                            pass
    
    with col2:
        st.header("📋 使用說明")
        
        st.markdown("""
        ### 🔄 處理流程
        1. **上傳音頻檔案**
           - 支援多種格式
           - 建議檔案小於 100MB
        
        2. **選擇模型大小**
           - Base 模型適合大多數情況
           - 檔案越大建議用越小的模型
        
        3. **選擇字幕類型**
           - 純中文：只有繁體中文
           - 雙語：原文 + 中文對照
        
        4. **下載字幕檔案**
           - 標準 SRT 格式
           - 可直接用於影片播放器
        
        ### ⚠️ 注意事項
        - 首次使用需下載模型
        - 處理時間取決於音頻長度
        - 建議音頻品質越高越好
        """)
        
        # 支援格式說明
        st.markdown("""
        ### 📁 支援格式
        - **音頻**: MP3, WAV, M4A, FLAC, OGG
        - **語言**: 99+ 種語言自動偵測
        - **輸出**: SRT 字幕檔案
        """)

if __name__ == "__main__":
    main()