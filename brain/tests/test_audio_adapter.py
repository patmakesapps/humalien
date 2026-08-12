import unittest

import numpy as np

from audio_adapter import ModelToPiAudio, PiToModelAudio


class AudioAdapterTests(unittest.TestCase):
    def test_pi_stereo_to_model_mono(self):
        # One second: 48,000 frames × 2 channels × 2 bytes.
        pi_audio = bytes(48_000 * 2 * 2)

        adapter = PiToModelAudio()
        model_audio = adapter.convert(pi_audio, final=True)

        # One second: 24,000 frames × 1 channel × 2 bytes.
        self.assertEqual(len(model_audio), 24_000 * 1 * 2)

        # Resampling silence can introduce harmless ±1 PCM dithering.
        model_samples = np.frombuffer(model_audio, dtype="<i2")
        self.assertLessEqual(
            np.max(np.abs(model_samples.astype(np.int32))),
            1,
        )

    def test_model_mono_to_pi_stereo(self):
        # One second: 24,000 frames × 1 channel × 2 bytes.
        model_audio = bytes(24_000 * 1 * 2)

        adapter = ModelToPiAudio()
        pi_audio = adapter.convert(model_audio, final=True)

        # One second: 48,000 frames × 2 channels × 2 bytes.
        self.assertEqual(len(pi_audio), 48_000 * 2 * 2)

        # Resampling silence can introduce harmless ±1 PCM dithering.
        pi_samples = np.frombuffer(pi_audio, dtype="<i2")
        self.assertLessEqual(
            np.max(np.abs(pi_samples.astype(np.int32))),
            1,
        )

    def test_buffers_incomplete_stereo_frame(self):
        # A pipe read can end part way through a frame. The leftover bytes
        # must be carried forward, not dropped, or the left and right
        # channels swap for the rest of the session.
        adapter = PiToModelAudio()

        adapter.convert(b"\x00\x00")
        self.assertEqual(adapter.residual, b"\x00\x00")

        adapter.convert(b"\x00\x00")
        self.assertEqual(adapter.residual, b"")

    def test_odd_split_keeps_sample_alignment(self):
        # A steady tone. If a chunk boundary ever misaligns the 16-bit
        # samples, the high and low bytes swap and the output turns to
        # noise instead of staying at the input level.
        level = 1_000
        pi_audio = np.full(48_000 * 2, level, dtype="<i2").tobytes()

        adapter = PiToModelAudio()

        # Split on a deliberately odd byte boundary.
        model_audio = adapter.convert(pi_audio[:1_001])
        model_audio += adapter.convert(pi_audio[1_001:], final=True)

        self.assertEqual(adapter.residual, b"")

        # Ignore the resampler's edge transients at each end.
        samples = np.frombuffer(model_audio, dtype="<i2")[100:-100]

        self.assertGreater(len(samples), 0)
        np.testing.assert_allclose(samples, level, atol=2)


if __name__ == "__main__":
    unittest.main()