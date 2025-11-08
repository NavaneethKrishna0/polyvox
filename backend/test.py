from TTS.api import TTS
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
print(tts.list_speaker_names())
