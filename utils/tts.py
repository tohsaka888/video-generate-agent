from indextts.infer import IndexTTS
from faster_whisper import WhisperModel

def generate_audio(text: str, audio_path: str, srt_path: str):
    tts = IndexTTS(model_dir="index-tts/checkpoints",cfg_path="index-tts/checkpoints/config.yaml")
    voice="assets/voice/zh.wav"
    text=text
    tts.infer(voice, text, audio_path)



    model_size = "large-v3"

    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    segments, info = model.transcribe(audio_path)

    print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

    for segment in segments:
        print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))

if __name__ == "__main__":
    generate_audio("你好，世界", "output.wav")