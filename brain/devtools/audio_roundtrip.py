import asyncio
import wave

from websockets.asyncio.client import connect

PI_IP = "10.0.0.83"
PORT = 8765

SAMPLE_RATE = 48000
CHANNELS = 2
SAMPLE_WIDTH = 2

SECONDS = 3
TARGET_BYTES = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH * SECONDS


async def main():
    uri = f"ws://{PI_IP}:{PORT}"

    print(f"Connecting to Humalien hardware node at {uri}...")

    async with connect(uri, max_size=None) as websocket:
        print("Connected.")
        print(f"Listening through Humalien for {SECONDS} seconds...")

        audio = bytearray()

        while len(audio) < TARGET_BYTES:
            message = await websocket.recv()

            if isinstance(message, bytes):
                audio.extend(message)

        audio = audio[:TARGET_BYTES]

        print(f"Received {len(audio)} bytes.")

        with wave.open("humalien-mic-test.wav", "wb") as wav:
            wav.setnchannels(CHANNELS)
            wav.setsampwidth(SAMPLE_WIDTH)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(audio)

        print("Saved humalien-mic-test.wav")
        print("Sending recording back to Humalien...")

        # Send the full recording at once so the Pi can buffer it
        # and play it continuously without chunk timing gaps.
        await websocket.send(bytes(audio))

        # Keep the connection open long enough for playback to finish.
        await asyncio.sleep(SECONDS + 0.5)

        print("Round-trip complete.")


if __name__ == "__main__":
    asyncio.run(main())
