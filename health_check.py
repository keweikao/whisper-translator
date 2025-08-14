#!/usr/bin/env python3
"""
健康檢查腳本 - 檢查所有依賴是否正常
"""
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_imports():
    """檢查所有必要的導入"""
    try:
        logger.info("檢查基本導入...")
        import gradio as gr
        logger.info(f"✅ Gradio {gr.__version__} 導入成功")
        
        import whisper
        logger.info("✅ OpenAI Whisper 導入成功")
        
        from deep_translator import GoogleTranslator
        logger.info("✅ Deep Translator 導入成功")
        
        import tempfile
        import os
        logger.info("✅ 系統模組導入成功")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 導入失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_translator():
    """檢查翻譯器功能"""
    try:
        logger.info("檢查翻譯器...")
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source='auto', target='zh-tw')
        result = translator.translate("Hello")
        logger.info(f"✅ 翻譯測試成功: {result}")
        return True
    except Exception as e:
        logger.error(f"❌ 翻譯器失敗: {str(e)}")
        return False

def check_whisper():
    """檢查 Whisper 模型載入"""
    try:
        logger.info("檢查 Whisper 模型...")
        import whisper
        # 嘗試載入最小模型
        model = whisper.load_model("tiny")
        logger.info("✅ Whisper 模型載入成功")
        return True
    except Exception as e:
        logger.error(f"❌ Whisper 模型失敗: {str(e)}")
        return False

def main():
    """主健康檢查"""
    logger.info("🔍 開始健康檢查...")
    
    checks = [
        ("基本導入", check_imports),
        ("翻譯器", check_translator),
        ("Whisper 模型", check_whisper)
    ]
    
    all_passed = True
    for name, check_func in checks:
        logger.info(f"📋 檢查 {name}...")
        if not check_func():
            all_passed = False
    
    if all_passed:
        logger.info("🎉 所有檢查通過！")
        return 0
    else:
        logger.error("💥 檢查失敗！")
        return 1

if __name__ == "__main__":
    sys.exit(main())