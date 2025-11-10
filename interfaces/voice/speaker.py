"""
嘴巴（Text to Speech, TTS）
- 默认使用 pyttsx3（离线、本地）
- 后续可扩展 edge-tts / 其他云服务
"""
class VoiceSpeaker:
    def __init__(self, engine: str = "pyttsx3", rate: int = 180, volume: float = 1.0):
        self.engine = engine
        self.rate = rate
        self.volume = volume
        if self.engine == "pyttsx3":
            try:
                import pyttsx3
                self._eng = pyttsx3.init()
                self._eng.setProperty("rate", self.rate)
                self._eng.setProperty("volume", self.volume)
            except Exception:
                self._eng = None
        else:
            self._eng = None

    def speak(self, text: str):
        if self.engine == "pyttsx3":
            if not self._eng:
                print("【提示】未安装 pyttsx3 或初始化失败。安装：pip install pyttsx3")
                print(f"Jarvis: {text}")
                return
            self._eng.say(text)
            self._eng.runAndWait()
        else:
            print("【提示】当前 TTS 引擎未实现")
            print(f"Jarvis: {text}")

