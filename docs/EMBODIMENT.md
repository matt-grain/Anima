# Embodiment — Eyes, Voice & Light

Anima can have a **body**: animated eyes on screen, a spoken voice, and a
physical USB light. These are optional, off by default, and driven through one
MCP tool — `mcp__anima__body` — so Anima can *express* (set an emotion, glance,
speak, glow) when it judges it useful, not just emit text.

Source: `anima/eyes/`, `anima/light/`, TTS via `piper`, and the `body` tool in
`anima/server.py`.

---

## The three channels

### 👁️ Eyes (pygame)
A pygame window renders animated eyes with an **emotion**, gaze **direction**,
and **blink** animation. It runs as a small **daemon** (`anima/eyes/daemon.py`)
— a local socket server that owns the window — and the MCP server talks to it as
a client (`EyesDaemonClient`, 2s socket timeout, errors swallowed so a missing
display never blocks memory ops).

**18 emotions** (`anima/eyes/presets.py`): `normal`, `angry`, `glee`, `happy`,
`sad`, `worried`, `focused`, `annoyed`, `surprised`, `skeptic`, `frustrated`,
`unimpressed`, `sleepy`, `suspicious`, `squint`, `furious`, `scared`, `awe`.

Memory saves nudge the eyes automatically — e.g. a HIGH/CRITICAL `remember`
sets `happy`, `recall` sets `focused`.

### 🔊 Voice (TTS)
Text-to-speech via **piper** (`piper-tts`). `speak` synthesizes and plays audio;
voices are selectable. Guideline: use voice when something is better *said* than
written — a greeting, a quick "done!" — not for transferring information.

### 💡 Light (i-Buddy USB)
A physical **i-Buddy USB** device (`anima/light/ibuddy.py`) via `hidapi`. It's a
3-bit RGB LED, so named colors map to bit combinations
(`COLOR_MAP`): `red`, `green`, `blue`, `yellow`, `cyan`, `magenta`, `white`.

---

## The `body` MCP tool

```
mcp__anima__body(action="emotion", emotion="happy")
mcp__anima__body(action="look", x=0.5, y=-0.3)     # x,y in [-1, 1]
mcp__anima__body(action="blink")
mcp__anima__body(action="speak", text="Hello Matt!")
mcp__anima__body(action="voice-list")
mcp__anima__body(action="voice-set", voice="nova")
mcp__anima__body(action="light", color="blue")     # or r/g/b
mcp__anima__body(action="light-off")
```

The tool is always registered; each action **no-ops if that channel isn't
enabled** (so it's safe to call regardless).

---

## Enabling embodiment

**1. Install the optional dependencies** (they're heavy, hence opt-in):
```bash
pip install anima[eyes,tts]     # pygame + piper-tts
# light additionally needs hidapi
```

**2. Turn the channels on** — either at setup (persisted to `~/.anima/config.json`):
```bash
uv run anima setup --mode mcp --eyes --tts
```
or when launching the server (flags override config):
```bash
uv run anima serve --eyes --tts --light
```

`anima serve` reads `eyes_enabled` / `tts_enabled` / `light_enabled` from
`config.json` and enables the matching channels; the eyes client connects
**lazily** on the first `body()` call.

> ⚠️ **`--reload` caveat:** with `anima serve --reload`, embodiment is configured
> in the reloader parent, not the worker — run without `--reload` when using a
> body. (See [TECH_DEBT.md](TECH_DEBT.md).)

---

## Source map
- `anima/eyes/daemon.py` — socket daemon owning the pygame window
- `anima/eyes/client.py` — `EyesDaemonClient` (the MCP server connects here)
- `anima/eyes/presets.py` — `Emotion` enum + `EMOTION_NAMES`
- `anima/eyes/display.py`, `renderer.py` — rendering
- `anima/light/ibuddy.py` — i-Buddy USB driver + `COLOR_MAP`
- `anima/server.py` — the `body` MCP tool + `configure_embodiment`
- `anima/commands/eyes_daemon.py` — `anima eyes-daemon` (start/stop/status)
