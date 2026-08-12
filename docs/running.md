# Running Humalien

## What goes on which machine

`git pull` brings the whole repo to both machines. That is fine — but only
install what each one actually runs. It is easy to `cd brain` on the Pi out of
habit and drag OpenCV onto a machine that never opens a camera.

**On the Pi, install this and nothing else:**

```bash
cd node
python -m pip install -r requirements.txt    # websockets, and that is all
sudo apt install alsa-utils                  # arecord and aplay
```

**Never install `brain/requirements.txt` on the Pi.**

| Package | Brain | Pi | Why |
| --- | --- | --- | --- |
| `websockets` | yes | **yes** | The link between them |
| `opencv-python` | yes | no | ~40 MB, and the Pi has no camera duties |
| `numpy` | yes | no | Only for resampling and matching |
| `soxr` | yes | no | The brain does all format conversion |
| `sounddevice` | yes | no | Desktop simulator only; the Pi uses ALSA directly |
| `python-dotenv` | yes | no | The Pi has no configuration to read |

The node also needs **none** of these:

- **The ONNX face models.** 38 MB of detector and recogniser that only the
  brain loads. Do not run `fetch_models.py` on the Pi.
- **`.env`, and therefore no OpenAI API key.** Worth being deliberate about:
  the Pi is the machine physically inside a robot that could be knocked over,
  handed to someone, or lost. It should hold no credentials at all.
- **`humalien.db`.** Who Humalien knows lives with the brain, which is also
  where it moves when the Asus becomes a Jetson.
- **Ollama.** The vision model is called from the brain.

This is not just tidiness. The node is a dumb pipe by design — `arecord` in,
`aplay` out — and keeping its dependency list to one package is what makes
that claim true rather than aspirational. It is also why swapping the brain
for a Jetson changes nothing on the Pi.

## Switching between the laptop and the Pi

One line decides which one the brain talks to:

```bash
HUMALIEN_PI_URL=ws://127.0.0.1:8765    # desktop simulator
HUMALIEN_PI_URL=ws://10.0.0.83:8765    # the real Pi
```

**Set it once.** `.env` is read last-value-wins, so if the key appears twice —
easy to end up with, since the desktop simulator needs a different value from
the default — only the bottom one takes effect. Editing the top one changes
nothing, and it looks exactly like a network fault: the brain sits there
failing to connect while the file plainly says the right address.

If a connection failure makes no sense, check for a second definition first:

```bash
grep -c HUMALIEN_PI_URL brain/.env    # should be 1
```

The same applies to every key in the file, but this is the one that bites,
because it is the only one that legitimately changes between sessions.

## The master file

`brain/humalien.py` is what the robot boots into. It checks the things
Humalien needs, says plainly what is missing, and then supervises the
conversation loop.

```bash
cd brain
python humalien.py
```

`voice_core.py` still runs standalone and is the better choice while
developing — a crash should be loud and immediate when you are working on it,
not quietly retried.

### What preflight checks

| Check | If missing |
| --- | --- |
| `.env` exists | **Fatal** |
| `OPENAI_API_KEY` set | **Fatal** — Humalien cannot talk |
| ONNX face models | **Degraded** — starts blind, with a warning |

Only the things that make Humalien impossible to run are fatal. Missing eyes
is a warning: a robot that can still hold a conversation is better than one
that refuses to boot.

### What supervision does

`voice_core.py` exits when any of its tasks finish, which is correct for
development and wrong for a robot. A dropped WiFi connection should not need
somebody to walk over and restart it.

The supervisor restarts the loop with backoff — 1 s, doubling to a 30 s
ceiling. A run that lasted longer than a minute is treated as healthy, so the
delay resets rather than punishing one late failure.

`SIGTERM` stops it cleanly, which is what systemd sends.

## Starting on boot

Units are in `deploy/`. They assume the repo lives at `/opt/humalien` and runs
as a `humalien` user.

**On the Pi:**

```bash
sudo cp deploy/humalien-node.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now humalien-node
journalctl -u humalien-node -f
```

**On the brain (Jetson):**

```bash
sudo cp deploy/humalien-brain.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now humalien-brain
journalctl -u humalien-brain -f
```

Both units set `Restart=always`. That is deliberate belt-and-braces: the brain
already reconnects on its own, so systemd is only there for what it cannot
recover from, such as the process being killed outright.

`SupplementaryGroups=video audio` is what gives the service access to the
camera and sound devices. Without it the service starts and then cannot see or
hear, which is a confusing failure to debug.

### Before enabling

- The `humalien` user needs to own `/opt/humalien` and be in the `video` and
  `audio` groups.
- `brain/.env` must exist on the brain with a real API key.
- `python tools/fetch_models.py` must have been run on the brain.
- On the Pi, check `ALSA_DEVICE` in `node/humalien_node/server.py` matches
  what `arecord -l` reports.

## Order of startup

The node is a server and the brain is a client, so the node should be up
first. In practice it does not matter: the brain retries until the node
answers, which is the whole point of the supervisor.

## Watching it work

Logs are tagged by layer, so it is clear which part is doing what:

```
[HUMALIEN]    startup, preflight, restarts
[VOICE CORE]  conversation, microphone gate, interruptions
[EYES]        camera, recognition
[TOOLS]       look / who_is_here / remember_name
```
