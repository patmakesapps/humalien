# People: identity, memory, and looking

Humalien should know who it is talking to, remember them tomorrow, and be able
to answer a question about what it can see — without a model running constantly
or a bill that scales with uptime.

## Three layers, three clocks

The whole design falls out of separating these. They run at wildly different
rates, and conflating them is what makes systems like this expensive.

| Layer | What runs | When | Cost |
| --- | --- | --- | --- |
| **Identity** | YuNet detect + SFace embed + dot product | Continuously, ~4 Hz | ~15 ms CPU. No model API. |
| **Talking** | OpenAI Realtime | Live conversation | The expensive one |
| **Looking** | Vision model over one frame | Only when the conversation asks | A few calls per conversation |
| **Writing** | Gemma over a finished transcript | After a conversation ends | A handful per day |

The important line is the first one. **Identity is not a language problem.**

## Why identity is an embedding, not an LLM

The instinct is to hand "who is this?" to a small vision model. Don't. A VLM
asked *"is this Patrick?"* is slow, costs a call every time, and is confidently
wrong in exactly the way that matters — it will say yes to the wrong person.

A face recognition net turns a face crop into a 128-dimensional unit vector.
Recognition is then cosine similarity against everyone known, which at
household scale is a dot product against a few dozen rows. Milliseconds, no
network, no tokens.

That single substitution is what makes always-on recognition viable. It was
only ever a resource problem because an LLM was doing an embedding's job.

`recognizer.py` uses SFace, paired with YuNet in `vision.py` — YuNet supplies
the five facial landmarks SFace needs to align a crop before embedding it.
Feeding SFace an unaligned crop quietly degrades matching for turned heads,
which are the ones we care about.

**Running recognition costs nothing.** No API, no tokens, no network. Only
`describe.py` and the Realtime session cost money.

## Only confirmed people are stored

This is the core v1 decision, and it is what keeps everything else simple.

```
face detected, nobody introduces them  → nothing stored
somebody says who they are             → enrolled, with a name
known face seen again                  → sighting recorded
```

`Perception.poll()` writes exactly one thing: a sighting of a person who is
*already known*. Enrolling is a deliberate act — `Perception.enroll()` — driven
by the conversation, never a side effect of being looked at.

### Why not track unknowns

The first version did, giving every unfamiliar face an anonymous record to be
named later. It was a mistake, and worth recording so it does not get
reinvented:

- A face caught mid-turn scores just below the match threshold and becomes a
  new record. One person quietly fragments into several.
- Those orphans then **steal sightings**, because matching takes the best face
  across everyone.
- Worse, a creation-time threshold cannot prevent it. A person's stored views
  accumulate, so a face that genuinely resembled nobody when first seen can
  match confidently later. Real measurements: one orphan reached **0.605**
  against the person it belonged to while still being a separate record.

That needed a movement check to reject photographs, a "too ambiguous to
enroll" band, a periodic consolidation pass, and a pruning policy — four
mechanisms, all defending against records nobody asked for.

Storing only confirmed people deletes the entire problem. A photograph on the
wall never introduces itself.

The cost is that Humalien cannot remember having *already asked* somebody who
declined to give a name, so it will ask again next time. Add that exception
the first time it is actually annoying, not before.

## Storage

SQLite, via stdlib `sqlite3`. Not because the data is large — it isn't — but
because **a robot head gets unplugged mid-write**. WAL mode gives atomic,
journaled writes. A JSON file rewrite does not.

```sql
people (id, name NOT NULL, first_seen_at, last_seen_at, sighting_count)
faces  (id, person_id, embedding BLOB, added_at)
facts  (id, person_id, text, source, created_at)
```

`name` is `NOT NULL`. The schema enforces the invariant: there is no such thing
as an anonymous person.

Embeddings are `BLOB`s, loaded into one numpy matrix at startup and cached.
**No vector index, no Chroma, no FAISS.** Brute force over thirty vectors is
microseconds; an index would be pure ceremony.

`faces` is deliberately many-per-person. One enrollment shot is fragile —
matching collapses under different lighting or angle. `record_sighting` adds a
new view only when it differs meaningfully from what is stored, capped at
`MAX_FACES_PER_PERSON`. This is safe now in a way it was not before: views are
only ever added to somebody already confidently matched.

`facts` rows hang off `person_id`, which is what lets memory about a person
survive a rename and accumulate across conversations.

## Thresholds

| Constant | Value | Meaning |
| --- | --- | --- |
| `MATCH_THRESHOLD` | 0.40 | Same person. |
| `GREET_THRESHOLD` | 0.50 | Confident enough to say the name out loud. |

SFace's documented operating point is 0.363; both are stricter, because using
the wrong name is worse than staying quiet.

### Measured on real faces

From a live session with two people, using the `d` key in `people_preview.py`:

| Comparison | Score |
| --- | --- |
| Same person, good look | 0.79 – 0.88 |
| Same person, awkward angle | ~0.38 |
| Two different people | ~0.28 |
| Unrelated faces | 0.02 – 0.25 |

Note the overlap: an awkward angle (0.38) scores lower than the threshold, and
not far above two different people (0.28). That narrow gap is exactly why
tracking unknowns was fragile, and why `d` exists — the winning similarity
alone looks healthy, and only the margin over the runner-up reveals trouble.

## Who writes what

The Realtime model talks. **Gemma does the writing**, over the finished
transcript, after the conversation ends.

- **Cost** — Realtime tokens are the expensive ones. Tool definitions sit in
  context all session and every call burns a round trip. Bookkeeping has no
  business there.
- **Latency** — fact extraction has zero urgency. It can run a minute later.
- **Better facts** — reading a whole transcript beats deciding turn by turn.
- **Re-runnable** — keep the transcripts and the extraction prompt can be
  improved and re-run over history.

**One exception: names write immediately.** If somebody says "I'm Derrick," the
rest of the conversation depends on it, and a crash would lose it. That is a
live tool call. The rule is *write immediately what the conversation depends
on, defer everything else.*

The transcripts are already arriving and being discarded —
`conversation.item.input_audio_transcription.completed` and
`response.output_audio_transcript.done` are both logged in `voice_core.py`
today.

## Looking

Looking is **pull-only**: it runs when the conversation model calls a tool,
never on a timer and never per frame. That single decision is what keeps the
cost bounded.

### Which frame

Not the current one. By the time a tool call arrives, the speaker has finished
talking, the model has generated a sentence, and **two to four seconds have
passed** — the hand being asked about has moved. Asking "how many fingers am I
holding up" and getting "the hand is blurred" is that gap, not a bad model.

`eyes.py` keeps the last few seconds of frames, already downscaled, with a
sharpness score for each. `look` asks for the clearest frame from the window
the person was actually speaking in — `speech_started_at` to
`speech_stopped_at`, which the session reports and which used to be logged and
thrown away.

Sharpest rather than nearest: a hand held up mid-sentence is usually moving,
and a blurred frame from exactly the right moment answers nothing.

Capture runs faster than recognition for the same reason. Recognition is happy
at 4 Hz; picking a sharp frame out of a moving hand needs candidates.

### Who does the looking

| `HUMALIEN_VISION` | What happens | Cost |
| --- | --- | --- |
| `realtime` | The frame is handed to the Realtime session, which looks itself | Image tokens on the expensive model |
| `ollama` | `gemma4:cloud` describes it, and the model reads the description | Free tier, **~8 s** |

`realtime` is the default. `gpt-realtime` accepts image input, so there is no
reason to make it read somebody else's description of a picture it could look
at — and it removes an eight-second silence from the middle of a conversation.

Two things to know about it. **Images stay in context**, so each look is
re-sent with every later turn; that is what makes follow-ups like "what about
the other hand" work without looking again, and it is also what makes the cost
grow. And it is a real reversal on price: Ollama's free tier cost nothing,
Realtime image tokens do. You are buying latency with money.

`ollama` remains for offline operation, and note that despite the name
`gemma4:cloud` is **not** local — frames leave the building. A genuinely local
model on the Jetson is the answer for privacy, more than for cost.

### When Realtime refuses

Sending an image is fire-and-forget over the websocket, so a rejection or rate
limit comes back as an asynchronous `error` event long after the tool returned.
That turn is already lost.

`voice_core.py` watches for it and permanently drops the session to Ollama, so
one failure costs one answer rather than every answer after it. A send that
fails outright is caught inline and falls back immediately.

Gemma has not left the project: text extraction from transcripts is still
exactly the job a cheap model should be doing.

## Try it

```bash
cd brain
python tools/fetch_models.py         # once per machine, ~38 MB
python tools/people_preview.py
```

| Key | Does |
| --- | --- |
| `n` | Introduce the largest face on screen |
| `d` | Score that face against everyone known |
| `l` | Ask a question about what the camera sees |
| `p` | List everyone Humalien knows |
| `f` | Forget somebody |
| `q` | Quit |

The database defaults to `brain/humalien.db` and is gitignored, as are the
downloaded models. Delete the `.db` to start over.

## One robot

`voice_core.py` now runs the camera alongside the conversation. Three tools are
declared on the session:

| Tool | Cost | When |
| --- | --- | --- |
| `who_is_here` | Free | Whenever the model needs to know who it is talking to |
| `remember_name` | A write | Once somebody introduces themselves |
| `look` | ~8 s, a call | Only when the answer requires seeing something |

`eyes.py` owns capture and recognition on a worker thread, so neither ever
stalls audio. Tool calls are dispatched as **separate tasks** rather than
awaited inline, for the same reason: `look` would otherwise block the event
loop that is feeding the speaker.

### The registry

Tools are declared in `robot_tools.py` with a decorator that keeps the schema
and the handler in one place:

```python
@tools.tool("look", "Look through your camera...",
            properties={"question": {"type": "string"}},
            required=["question"])
async def look(robot: Robot, question: str) -> dict:
```

`tool_registry.py` turns those into the `session.tools` payload, validates
incoming arguments, and runs the handler. Three things it buys:

- **No drift.** A schema and a dispatch table maintained separately fail only
  when the model calls the tool. A test now asserts every handler can accept
  what its schema declares.
- **Forgiving coercion.** Models send `"2"` for `2` and `"yes"` for `true`
  constantly. Those are corrected rather than failed.
- **One error contract.** Everything comes back as `{"success": ..., "data"}`
  or `{"success": false, "error"}`. A tool that broke can never come back
  looking like one that worked and happened to mention an error — raising
  `ToolError` sends the message straight to the model, which can act on it.

### Arrivals are pushed, depth is pulled

The model has no reason to suspect the room changed, so it will never call a
tool to find out. `watch_the_room` pushes a system message when somebody walks
into view, along with anything remembered about them, and asks for a response
so Humalien greets them unprompted.

Everything else stays pull-only. Pushing is reserved for what the model cannot
discover by asking.

Both pushes are suppressed while the model is answering or the head is still
speaking, so an arrival never talks over a conversation in progress. Somebody
out of view for `FORGET_PRESENCE_AFTER` counts as a fresh arrival when they
return, which stops a flicker in tracking from re-triggering a greeting.

## Not built yet

- **Transcripts and fact extraction** — persist both sides, then run Gemma over
  a finished conversation. Until this lands, `facts` is only written by hand,
  so Humalien remembers *who* you are but not what you talked about.
- **Who is *talking*** — face-in-room is not the same question as
  who-is-speaking. With two people in frame nothing decides which is the
  speaker. The answer is the same architecture again: voice embeddings in a
  `voices` table beside `faces`, auto-enrolled whenever exactly one known face
  is present and somebody speaks. `input_audio_buffer.speech_started` and
  `speech_stopped` already bracket each utterance for free.
