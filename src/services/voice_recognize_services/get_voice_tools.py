import sounddevice as sd
from loguru import logger


def get_voice_tools(duration=5, fs=16000):
    """录制语音并返回 numpy 数组"""
    logger.info(f"请开始说话（录音 {duration} 秒）...")
    # 录制音频，直接获取 float32 格式的 numpy 数组
    audio_data = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
    sd.wait()  # 等待录音结束
    logger.info("录音结束...")

    # 返回一维数组
    return audio_data.flatten()

