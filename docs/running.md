# Running Humalien

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
