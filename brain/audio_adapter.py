import numpy as np
import soxr


PI_SAMPLE_RATE = 48_000
PI_CHANNELS = 2

MODEL_SAMPLE_RATE = 24_000
MODEL_CHANNELS = 1


class PiToModelAudio:
    """Convert Pi PCM16 audio from 48 kHz stereo to 24 kHz mono."""

    def __init__(self):
        self.resampler = soxr.ResampleStream(
            PI_SAMPLE_RATE,
            MODEL_SAMPLE_RATE,
            MODEL_CHANNELS,
            dtype="int16",
            quality="HQ",
        )

    def convert(self, audio: bytes, *, final: bool = False) -> bytes:
        samples = np.frombuffer(audio, dtype="<i2")

        if len(samples) % PI_CHANNELS != 0:
            raise ValueError("Pi audio does not contain complete stereo frames")

        stereo = samples.reshape(-1, PI_CHANNELS)

        # Average left and right without overflowing a 16-bit integer.
        mono = (
            stereo.astype(np.int32)
            .mean(axis=1)
            .clip(-32768, 32767)
            .astype(np.int16)
        )

        converted = self.resampler.resample_chunk(mono, last=final)
        return converted.astype("<i2", copy=False).tobytes()


class ModelToPiAudio:
    """Convert model PCM16 audio from 24 kHz mono to 48 kHz stereo."""

    def __init__(self):
        self.resampler = soxr.ResampleStream(
            MODEL_SAMPLE_RATE,
            PI_SAMPLE_RATE,
            MODEL_CHANNELS,
            dtype="int16",
            quality="HQ",
        )

    def convert(self, audio: bytes, *, final: bool = False) -> bytes:
        mono = np.frombuffer(audio, dtype="<i2")

        converted = self.resampler.resample_chunk(mono, last=final)

        # Send the same signal through the Pi's left and right channels.
        stereo = np.repeat(converted[:, np.newaxis], PI_CHANNELS, axis=1)

        return stereo.astype("<i2", copy=False).tobytes()