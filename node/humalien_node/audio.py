from pathlib import Path
import subprocess

ALSA_DEVICE = "hw:2,0"
SAMPLE_RATE = 48000
CHANNELS = 2
FORMAT = "S16_LE"


def record(output_path: str | Path, seconds: int = 3) -> Path:
    output_path = Path(output_path)

    cmd = [
        "arecord",
        "-D", ALSA_DEVICE,
        "-f", FORMAT,
        "-r", str(SAMPLE_RATE),
        "-c", str(CHANNELS),
        "-d", str(seconds),
        str(output_path),
    ]

    subprocess.run(cmd, check=True)
    return output_path


def play(input_path: str | Path) -> None:
    input_path = Path(input_path)

    cmd = [
        "aplay",
        "-D", ALSA_DEVICE,
        str(input_path),
    ]

    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    test_file = Path("/tmp/humalien-audio-test.wav")

    print("Humalien: recording for 3 seconds...")
    record(test_file, seconds=3)

    print("Humalien: playing recording...")
    play(test_file)

    print("Humalien audio test complete.")
