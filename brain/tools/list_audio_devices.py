import sounddevice as sd


def main() -> None:
    print("Audio devices visible to the desktop node simulator.\n")
    print(sd.query_devices())

    default_input, default_output = sd.default.device

    print(f"\nDefault input:  {default_input}")
    print(f"Default output: {default_output}")

    print(
        "\nPick a real microphone for HUMALIEN_DESKTOP_INPUT_DEVICE.\n"
        "Loopback devices (Stereo Mix, What U Hear, virtual cables) feed\n"
        "the speaker straight back into the model and it will answer itself."
    )


if __name__ == "__main__":
    main()
