"""Sleep is a mute, so the tests are mostly about what stays shut."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import voice_core
from audio_adapter import WAKE_SAMPLE_RATE, PiToModelAudio
from conversation import ConversationState
from mic_gate import HalfDuplexGate, OpenGate, SleepableGate
from mood import Mood
from robot_tools import Robot, tools
from waking import WakeWord, heard_wake_word


# 200 ms of 48 kHz stereo PCM16. Longer than the Pi's 20 ms chunk on
# purpose: soxr buffers, and one chunk in gets nothing back out, so a test
# built on a single chunk sees an empty send and blames the mute.
SILENCE = bytes(2 * 2 * 9600)


class FakePlayback:
    def __init__(self, speaking=False):
        self.is_speaking = speaking


class FakeRecognizer:
    """Stands in for Vosk, which needs a 50 MB model and a microphone."""

    def __init__(self, finals=(), partials=()):
        self.finals = list(finals)
        self.partials = list(partials)
        self.reset_calls = 0

    def AcceptWaveform(self, audio):
        """True only when a phrase has ended, which is the real behaviour.

        Vosk emits a final on endpointing - the silence after the words -
        so a clip that stops the instant the word does never produces one.
        """

        return bool(self.finals)

    def Result(self):
        return self.finals.pop(0) if self.finals else '{"text": ""}'

    def PartialResult(self):
        return self.partials.pop(0) if self.partials else '{"partial": ""}'

    def Reset(self):
        self.reset_calls += 1


class SleepableGateTests(unittest.TestCase):
    def test_open_gate_closes_when_asleep(self):
        state = ConversationState()
        gate = SleepableGate(OpenGate(FakePlayback()), state)

        self.assertTrue(gate.is_open)

        state.asleep = True
        self.assertFalse(gate.is_open)

    def test_waking_reopens_it(self):
        state = ConversationState()
        gate = SleepableGate(OpenGate(FakePlayback()), state)

        state.asleep = True
        state.asleep = False

        self.assertTrue(gate.is_open)

    def test_sleep_and_half_duplex_close_it_independently(self):
        state = ConversationState()
        playback = FakePlayback(speaking=True)
        gate = SleepableGate(HalfDuplexGate(playback), state)

        # Shut because the robot is talking.
        self.assertFalse(gate.is_open)

        # Still shut when it stops, because it is also asleep.
        state.asleep = True
        playback.is_speaking = False
        self.assertFalse(gate.is_open)

        # And only open once both reasons are gone.
        state.asleep = False
        self.assertTrue(gate.is_open)


class SleepingEyesTests(unittest.TestCase):
    def test_eyes_go_out(self):
        mood = Mood(websocket=None)
        mood.sleep(True)

        self.assertEqual(mood.decide(0.1), ("off", 0.0))

    def test_sleep_beats_a_feeling_that_has_not_expired(self):
        mood = Mood(websocket=None)
        mood.feel("happy")
        mood.sleep(True)

        self.assertEqual(mood.decide(0.1)[0], "off")

    def test_a_new_face_does_not_light_a_sleeping_robot(self):
        mood = Mood(websocket=None)
        mood.sleep(True)
        mood.seen(new=True)

        self.assertEqual(mood.decide(0.1)[0], "off")

    def test_it_stops_looking_at_whoever_it_was_watching(self):
        """Half of each eye stayed lit on a robot that was supposed to be off.

        The node paints the gaze highlight whatever the mood is, so a gaze
        left over from the moment it fell asleep kept burning.
        """

        mood = Mood(websocket=None)
        mood.look_at(0.6)
        mood.sleep(True)

        self.assertIsNone(mood.gaze)

    def test_waking_returns_to_a_normal_mood(self):
        mood = Mood(websocket=None)
        mood.sleep(True)
        mood.decide(0.1)
        mood.sleep(False)

        self.assertNotEqual(mood.decide(0.1)[0], "off")


class WakeWordTests(unittest.TestCase):
    def test_phrases_that_should_wake_it(self):
        for phrase in ("tubby", "hey tubby", "ok tubby", "wake up"):
            self.assertTrue(heard_wake_word(phrase), phrase)

    def test_case_and_spacing_do_not_matter(self):
        self.assertTrue(heard_wake_word("  HEY   TUBBY "))

    def test_silence_does_not_wake_it(self):
        self.assertFalse(heard_wake_word(""))
        self.assertFalse(heard_wake_word("   "))

    def test_other_talk_does_not_wake_it(self):
        for phrase in ("what time is it", "chubby", "the tub"):
            self.assertFalse(heard_wake_word(phrase), phrase)

    def test_a_final_result_wakes_it(self):
        waker = WakeWord(FakeRecognizer(finals=['{"text": "hey tubby"}']))

        self.assertTrue(waker.feed(SILENCE))

    def test_a_partial_does_not_wake_it(self):
        """The decoder revises partials, and revises through the wake words.

        Recorded from the real model: "what time is it tomorrow afternoon"
        partials as `wake`, then `wake tubby`, before settling on `[unk]`
        in the final. Waking on a partial turns a robot somebody muted back
        on because they said "tomorrow".
        """

        waker = WakeWord(FakeRecognizer(partials=['{"partial": "wake tubby"}']))

        self.assertFalse(waker.feed(SILENCE))

    def test_unrelated_speech_does_not(self):
        waker = WakeWord(FakeRecognizer(finals=['{"text": "[unk]"}']))

        self.assertFalse(waker.feed(SILENCE))

    def test_reset_clears_the_phrase_that_woke_it(self):
        recognizer = FakeRecognizer()
        WakeWord(recognizer).reset()

        self.assertEqual(recognizer.reset_calls, 1)


class SleepToolTests(unittest.IsolatedAsyncioTestCase):
    def build(self, mood=None):
        self.state = ConversationState()

        return Robot(
            eyes=None,
            store=None,
            describer=None,
            state=self.state,
            mood=mood,
        )

    async def run_tool(self, robot, name, arguments=None):
        return json.loads(await tools.execute(robot, name, arguments))

    async def test_it_closes_the_microphone(self):
        robot = self.build()

        self.assertFalse(self.state.asleep)

        result = await self.run_tool(robot, "sleep")

        self.assertTrue(result["success"])
        self.assertTrue(result["data"]["asleep"])
        self.assertTrue(self.state.asleep)

    async def test_it_records_when_so_the_sleep_can_time_out(self):
        robot = self.build()
        await self.run_tool(robot, "sleep")

        self.assertIsNotNone(self.state.slept_at)

    async def test_it_puts_the_eyes_out(self):
        mood = Mood(websocket=None)
        robot = self.build(mood=mood)

        await self.run_tool(robot, "sleep")

        self.assertTrue(mood.asleep)
        self.assertEqual(mood.decide(0.1), ("off", 0.0))

    async def test_asking_twice_is_harmless(self):
        robot = self.build()

        await self.run_tool(robot, "sleep")
        first = self.state.slept_at

        await self.run_tool(robot, "sleep")

        self.assertTrue(self.state.asleep)
        self.assertEqual(self.state.slept_at, first)

    async def test_it_works_without_eyes(self):
        robot = self.build(mood=None)

        result = await self.run_tool(robot, "sleep")

        self.assertTrue(result["data"]["asleep"])


class FakeWebsocket:
    def __init__(self, messages):
        self.messages = messages

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for message in self.messages:
            yield message


class FakeRealtime:
    def __init__(self):
        self.sent = []

    async def send_audio(self, audio):
        self.sent.append(audio)


class AlwaysWakes:
    def __init__(self):
        self.reset_calls = 0

    def feed(self, audio):
        return True

    def reset(self):
        self.reset_calls += 1


class PumpTests(unittest.IsolatedAsyncioTestCase):
    """The loop the mute actually runs in."""

    async def pump(self, messages, state, waker=None):
        await voice_core._pump_microphone(
            FakeWebsocket(messages),
            FakeRealtime(),
            SleepableGate(OpenGate(FakePlayback()), state),
            None,
            PiToModelAudio(),
            True,
            state,
            waker,
            PiToModelAudio(WAKE_SAMPLE_RATE) if waker else None,
        )

    async def test_a_pi_status_message_does_not_clobber_the_mute(self):
        """This crashed the robot a second after the Pi connected.

        `node_status` carries a field called "state", and assigning it to a
        local of the same name replaced the ConversationState with the
        string "ready". The next chunk of audio asked "ready" whether it
        was asleep.
        """

        state = ConversationState()
        state.asleep = True

        # A whole 20 ms of 48 kHz stereo, so the resampler has something to
        # hand the wake word listener.
        audio = SILENCE

        await self.pump(
            ['{"type": "node_status", "node": "humalien-pi", "state": "ready"}', audio],
            state,
            waker=AlwaysWakes(),
        )

        self.assertFalse(state.asleep)

    async def test_it_does_not_wake_itself_up_saying_goodnight(self):
        """It woke on its own name, every time, before this.

        There is no echo cancellation, so the microphone hears the speaker.
        The goodnight ends "say my name" and the wake word listener heard
        exactly that.
        """

        state = ConversationState()
        state.asleep = True

        speaking = FakePlayback(speaking=True)
        waker = AlwaysWakes()

        await voice_core._pump_microphone(
            FakeWebsocket([SILENCE]),
            FakeRealtime(),
            SleepableGate(HalfDuplexGate(speaking), state),
            None,
            PiToModelAudio(),
            True,
            state,
            waker,
            PiToModelAudio(WAKE_SAMPLE_RATE),
        )

        self.assertTrue(state.asleep)

    async def test_it_does_wake_once_the_room_is_the_only_voice(self):
        state = ConversationState()
        state.asleep = True

        await voice_core._pump_microphone(
            FakeWebsocket([SILENCE]),
            FakeRealtime(),
            SleepableGate(HalfDuplexGate(FakePlayback(speaking=False)), state),
            None,
            PiToModelAudio(),
            True,
            state,
            AlwaysWakes(),
            PiToModelAudio(WAKE_SAMPLE_RATE),
        )

        self.assertFalse(state.asleep)

    async def test_audio_is_withheld_while_asleep(self):
        state = ConversationState()
        state.asleep = True

        realtime = FakeRealtime()
        await voice_core._pump_microphone(
            FakeWebsocket([SILENCE]),
            realtime,
            SleepableGate(OpenGate(FakePlayback()), state),
            None,
            PiToModelAudio(),
            True,
            state,
            None,
            None,
        )

        self.assertEqual(realtime.sent, [])

    async def test_audio_flows_again_once_awake(self):
        state = ConversationState()

        realtime = FakeRealtime()
        await voice_core._pump_microphone(
            FakeWebsocket([SILENCE]),
            realtime,
            SleepableGate(OpenGate(FakePlayback()), state),
            None,
            PiToModelAudio(),
            True,
            state,
            None,
            None,
        )

        self.assertTrue(realtime.sent)


if __name__ == "__main__":
    unittest.main()
