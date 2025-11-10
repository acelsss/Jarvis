"""
耳朵（Speech to Text, STT）
- 优先使用 speech_recognition + 系统麦克风
- 后续可切换到 whisper/vosk 等离线方案
"""
from typing import Optional

class VoiceListener:
    def __init__(self, engine: str = "speech_recognition", language: str = "zh-CN"):
        self.engine = engine
        self.language = language

    def listen_once(self) -> Optional[str]:
        if self.engine == "speech_recognition":
            try:
                import speech_recognition as sr
            except Exception:
                return "【提示】未安装 speech_recognition，无法使用语音输入。请先安装：pip install SpeechRecognition pyaudio（或 sounddevice）"
            r = sr.Recognizer()
            with sr.Microphone() as source:
                print("🎧 请开始说话（静音环境更佳）...")
                audio = r.listen(source)
            try:
                text = r.recognize_google(audio, language=self.language)
                return text
            except Exception as e:
                return f"【识别失败】{e}"
        else:
            return "【提示】当前 STT 引擎未实现"

    def stream(self):
        # 预留连续流接口（后续实现）
        raise NotImplementedError("stream() 尚未实现")

