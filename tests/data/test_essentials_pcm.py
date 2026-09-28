"""Essentials rebuilding must work without macOS-specific codec services."""
import hashlib
import struct
import wave

from scripts.import_essentials import decode_source_pcm


def test_decode_original_to_portable_mono_pcm_without_changing_source(tmp_path):
    original = tmp_path / 'original.wav'
    with wave.open(str(original), 'wb') as source:
        source.setnchannels(2)
        source.setsampwidth(2)
        source.setframerate(8000)
        source.writeframes(b''.join(struct.pack('<hh', 1200, -400) for _ in range(2000)))
    before = hashlib.sha256(original.read_bytes()).hexdigest()
    decoded = tmp_path / 'decoded.wav'
    decode_source_pcm(original, decoded)
    with wave.open(str(decoded), 'rb') as result:
        assert (result.getnchannels(), result.getsampwidth(), result.getframerate()) == (1, 2, 16000)
        assert abs(result.getnframes() - 4000) <= 1
        assert result.readframes(result.getnframes()) != b'\0\0' * result.getnframes()
    assert hashlib.sha256(original.read_bytes()).hexdigest() == before
