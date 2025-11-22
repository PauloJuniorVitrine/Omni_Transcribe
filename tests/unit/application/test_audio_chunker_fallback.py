from pathlib import Path
import wave

from application.services.audio_chunker import AudioChunker


def _write_silence_wav(path: Path, seconds: int = 2, sample_rate: int = 16000):
    # 1-channel 16-bit silence
    frames = b"\x00\x00" * sample_rate * seconds
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def test_audio_chunker_fallback_splits_wav_without_pydub(tmp_path):
    wav = tmp_path / "test.wav"
    _write_silence_wav(wav, seconds=2, sample_rate=8000)  # 2s
    chunker = AudioChunker(chunk_duration_sec=1)

    chunks = chunker.split(wav)

    assert len(chunks) == 2
    assert abs(chunks[0].duration_sec - 1.0) < 0.1
    assert chunks[0].path.exists()
