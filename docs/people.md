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

`describe.py` is the expensive path, so it is **pull-only**: it runs when the
conversation model calls a tool, never on a timer and never per frame. That
single decision is worth more than any local-vs-cloud choice.

Frames are downscaled to 512 px on the longest edge. Bigger images cost more
and answer no better for "what is this" questions. The describer takes the
**user's actual question**, so the answer is short and targeted rather than a
paragraph of caption to read aloud.

### Model

`gemma4:cloud` via Ollama — multimodal, on the free cloud tier. Note that
despite running through Ollama it is **not local**: frames leave the building
on every call. That is a privacy consideration for a robot in a house, and a
better argument for a local model on the Jetson than cost is.

**Measured latency: about 8 seconds cold.** That is a long silence. Humalien
needs to say "let me look" *before* the call fires, or the pause reads as a
crash. Treat that as a requirement, not a nicety.

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

## Not built yet

Perception, the store, and the describer all work and are testable. What is not
wired:

- **Realtime tool wiring** — `session.tools` with `look`, `who_is_here` and
  `remember_name`, plus a `function_call_output` handler in `voice_core.py`.
  Until this lands, voice and vision are separate programs.
- **Identity push** — when a known person appears, the model should be told
  unprompted so it can greet them. Depth about a person stays pull-only.
- **Transcripts and fact extraction** — persist both sides, then run Gemma over
  a finished conversation.
- **Who is *talking*** — face-in-room is not the same question as
  who-is-speaking. With two people in frame nothing decides which is the
  speaker. The answer is the same architecture again: voice embeddings in a
  `voices` table beside `faces`, auto-enrolled whenever exactly one known face
  is present and somebody speaks. `input_audio_buffer.speech_started` and
  `speech_stopped` already bracket each utterance for free.
