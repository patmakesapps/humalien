"""What the conversation is doing right now.

Shared between the event loop and the tools, so a tool can ask when the
person was actually speaking rather than guessing from the clock.
"""


class ConversationState:
    def __init__(self) -> None:
        # True between response.created and response.done, so nothing
        # interrupts the model mid-answer.
        self.response_active = False

        # When the user was last talking. A question is asked during this
        # window, which is the moment worth looking at - not the moment the
        # tool call finally arrives, seconds later.
        self.speech_started_at: float | None = None
        self.speech_stopped_at: float | None = None

        # Muted. Not a mood and not a pause: while this is set the
        # microphone never reaches the Realtime API at all, so there is
        # nothing for the model to answer and nothing it can decide to
        # answer anyway. Enforced in the gate rather than in the persona,
        # because a mute the model can talk itself out of is not a mute.
        self.asleep = False

        # When it went to sleep, so a wake that never comes can time out.
        self.slept_at: float | None = None

    def speech_window(self) -> tuple[float | None, float | None]:
        """The span the last question was asked in, if there was one."""

        if self.speech_started_at is None:
            return None, None

        return self.speech_started_at, self.speech_stopped_at
