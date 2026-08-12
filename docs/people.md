# People: identity, memory, and looking

Humalien should know who walked into the room, remember them tomorrow, and be
able to answer a question about what it can see — without a model running
constantly or a bill that scales with uptime.

## Three layers, three clocks

The whole design falls out of separating these. They run at wildly different
rates, and conflating them is what makes systems like this expensive.

| Layer | What runs | When | Cost |
| --- | --- | --- | --- |
| **Identity** | YuNet detect + SFace embed + dot product | Continuously, ~4 Hz | ~15 ms CPU. No model API. |
| **Looking** | Vision model over one frame | Only when the conversation asks | One call, a few per conversation |
| **Consolidation** | Small LLM over a finished transcript | After a conversation ends | Handful per day, nobody waiting |

The important line is the first one. **Identity is not a language problem.**

## Why identity is an embedding, not an LLM

The instinct is to hand "who is this?" to a small vision model. Don't. A VLM
asked *"is this Patrick?"* is slow, costs a call every time, and is confidently
wrong in exactly the way that matters — it will say yes to the wrong person.

A face recognition net turns a face crop into a 128-dimensional unit vector.
Recognition is then cosine similarity against everyone seen before, which at
household scale is a dot product against a few dozen rows. Milliseconds, no
network, no tokens.

That single substitution is what makes the "can't have it constantly running"
problem disappear. It was only a problem because an LLM was doing an
embedding's job.

`recognizer.py` uses SFace, paired with YuNet in `vision.py` — YuNet supplies
the five facial landmarks SFace needs to align a crop before embedding it.
Feeding SFace an unaligned crop quietly degrades matching for turned heads,
which are the ones we care about.

## Storage

SQLite, via stdlib `sqlite3`. Not because the data is large — it isn't — but
because **a robot head gets unplugged mid-write**. WAL mode gives atomic,
journaled writes. A JSON file rewrite does not.

```sql
people (id, name, name_source, first_seen_at, last_seen_at, sighting_count)
faces  (id, person_id, embedding BLOB, added_at)
facts  (id, person_id, text, source, created_at)
```

Embeddings are `BLOB`s, loaded into one numpy matrix at startup and cached.
**No vector index, no Chroma, no FAISS.** Brute force over thirty vectors is
microseconds; an index would be pure ceremony.

`faces` is deliberately many-per-person. One enrollment shot is fragile —
matching collapses under different lighting or angle. `record_sighting` adds a
new view only when it differs meaningfully from what's stored (cosine below
`NOVEL_BELOW`), capped at `MAX_FACES_PER_PERSON`. That one detail is most of
the difference between recognition that feels magic and recognition that keeps
forgetting you.

## The unknown-face lifecycle

There is **no separate table for unconfirmed people.** `name IS NULL` means
unidentified. A person is a person whether or not you know what to call them.

Two tables would mean rewriting foreign keys from `faces` and `facts` on
promotion, duplicating schema, and turning "we learned their name" into a
migration. Instead:

```sql
UPDATE people SET name = ?, name_source = 'asked' WHERE id = ?
```

Every embedding and fact already attached comes along for free.

The part that makes it work is that **every detection matches against everyone,
named or not**:

```
detect → embed → match against all people
  ├─ matches a named person    → greet them
  ├─ matches an unnamed person → attach the sighting to that record
  └─ matches nobody            → create a new record, name NULL
```

So unnamed people accumulate embeddings and history *before* you know who they
are. Learn the name later and all of it attaches retroactively — the robot can
say "you were here Tuesday too." That behavior is free; it falls out of the
schema.

### Thresholds

| Constant | Value | Meaning |
| --- | --- | --- |
| `MATCH_THRESHOLD` | 0.40 | Same person. Attach the sighting. |
| `GREET_THRESHOLD` | 0.50 | Confident enough to say the name out loud. |

SFace's documented operating point is 0.363; both are stricter. The failure
costs aren't symmetric:

- **Two people merged into one record** — bad. Mixed embeddings poison the
  record and you will eventually name it wrong.
- **One person split into two records** — mild. Duplicate unknowns.

So both cutoffs stay strict and we accept some splitting, with
`PeopleStore.merge()` as the repair. Without a merge you'd be hand-editing the
database after every clustering mistake.

## When to ask a name

Not on first detection — someone crossing the frame shouldn't trigger an
interrogation. `Sighting.should_ask_name()` waits until the face has been
present for `SECONDS_BEFORE_ASKING_NAME`, which is the natural conversational
moment and the point at which you'd get a real answer.

Enrollment should be **conversational**, not silent. Unknown face appears,
Humalien says "I don't think we've met." That's better UX than a robot quietly
building dossiers on house guests, and it attaches a name at the moment of
capture instead of leaving an orphaned vector to label later.

## Two things that will bite you

**Junk accumulation.** A camera in a room will enroll the mailman, a delivery
driver, and faces on the television. `prune_unnamed()` forgets unnamed records
with few sightings that haven't been seen in a while. Named people are never
touched.

**Static faces.** A photo on the wall is a perfect, permanently detected face.
`Sighting.looks_alive` requires both a run of consecutive frames *and* actual
movement before committing anyone to the database — a photograph never shifts
by a pixel, a real face never holds still.

## Looking

`describe.py` is the expensive path, so it is **pull-only**: it runs when the
conversation model calls a tool, never on a timer and never per frame. That
single decision is worth more than any local-vs-cloud choice — it's the
difference between a handful of calls per conversation and thirty per second.

Frames are downscaled to 512 px on the longest edge before encoding. Bigger
images cost more and answer no better for "what is this" questions.

The describer takes the **user's actual question**, not a generic "describe this
image". You get a targeted, short answer instead of a paragraph of caption to
read aloud.

### Model

`gemma4:cloud` via Ollama — multimodal, and available on Ollama's free cloud
tier. Swap with `--model` or run a local model with the same interface; the
call shape is identical either way.

**Measured latency: about 8 seconds cold.** That is a long silence in a
conversation. When this is wired into the voice loop, Humalien needs to say
"let me look" *before* the call, or the pause reads as a crash. Treat that as a
requirement, not a nicety.

## Try it

```bash
cd brain
python tools/fetch_models.py         # once per machine, ~38 MB
python tools/people_preview.py
```

| Key | Does |
| --- | --- |
| `n` | Name the largest face on screen |
| `l` | Ask a question about what the camera sees |
| `p` | List everyone Humalien has met |
| `q` | Quit |

The database defaults to `brain/humalien.db` and is gitignored, as are the
downloaded models. Delete the `.db` to start over.

## Not built yet

The perception layer, the store, and the describer all work and are testable.
What isn't wired:

- **Realtime tool wiring** — `session.tools` with `look` and `recall_person`,
  plus a `function_call_output` handler in `voice_core.py`.
- **Identity push** — when a known person appears, the model should be told
  unprompted so it can greet them. Depth about a person stays pull-only;
  identity is small enough to push.
- **Consolidation** — the small LLM that turns a finished transcript into rows
  in `facts`.
- **Who is *talking*** — face-in-room is not the same question as
  who-is-speaking. With two people in frame, nothing currently decides which
  one is the speaker. Largest/most central face is the cheap first answer;
  audio speaker embeddings are the real one.
