"""Build the narrated HireGuard explainer video.

Pipeline:
  1. macOS `say` -> one audio clip per narration line; measure each duration.
  2. Compute beat offsets so each agent activates exactly when it is named.
  3. Render explainer_vo.html with the EVENTS timeline injected.
  4. Capture frames deterministically over Chrome's virtual clock.
  5. Mux narration (clips + gaps + tail) with the frames -> explainer_narrated.mp4.
"""
from __future__ import annotations

import asyncio
import base64
import json
import subprocess
import urllib.request
from pathlib import Path

import websockets

HERE = Path(__file__).resolve().parent
TMP = HERE / "_vo"
FRAMES = HERE / "_frames"
VOICE = "Samantha"
RATE = 160         # calmer cadence
FPS = 30
DT = 1000.0 / FPS
SCALE = 1.5
W, H = 1280, 720
LEAD = 0.6         # s of silence before narration starts
GAP = 0.52         # s between lines — lets each sentence breathe
TAIL = 2.9         # s hold on the verdict after the last line
STARVATION = 1_000_000

LINES = [
    "Every job posting is a legal minefield: federal discrimination law, plus a patchwork of state pay-transparency rules.",
    "HireGuard audits it with a team of four AI agents, collaborating live in a Band room.",
    "First, Intake reads the hiring packet and extracts the facts.",
    "PolicyAgent applies the compliance ruleset and cites every candidate violation.",
    "RiskScorer sends each finding to the AI and ML scoring API, rating its legal exposure from zero to one hundred.",
    "Then Counsel reviews the case, and can bounce a weak finding back to Policy Agent for another look.",
    "The result: a defensible, cited audit memo. Verdict, high. Ready for human sign-off.",
]


def sh(*args: str) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()


def dur(path: Path) -> float:
    return float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", str(path)))


def build_audio_and_events():
    TMP.mkdir(exist_ok=True)
    for f in TMP.glob("*"):
        f.unlink()

    clips, durs = [], []
    for i, line in enumerate(LINES):
        aiff = TMP / f"l{i}.aiff"
        wav = TMP / f"l{i}.wav"
        subprocess.run(["say", "-v", VOICE, "-r", str(RATE), "-o", str(aiff), line], check=True)
        subprocess.run(["ffmpeg", "-y", "-i", str(aiff), "-ar", "44100", "-ac", "2", str(wav)],
                       capture_output=True, check=True)
        clips.append(wav)
        durs.append(dur(wav))

    starts = []
    t = LEAD
    for d in durs:
        starts.append(t)
        t += d + GAP
    content_end = starts[-1] + durs[-1]
    total_s = content_end + TAIL
    total_ms = int(total_s * 1000)

    def ms(x): return int(round(x * 1000))

    # gentle baton-pass: prev finishes during the gap, the connector token
    # travels, the next agent wakes just as the new sentence begins.
    def ho(prev, c, nxt, s):
        return [[ms(s - 0.46), "finish", prev], [ms(s - 0.40), "conn", c], [ms(s + 0.12), "activate", nxt]]

    ev = [[0, "plab", "reading the posting…"]]
    # L1 — "a team of four AI agents": gentle sweep that introduces each card
    s1 = starts[1]
    ev.append([ms(s1 + 0.15), "plab", "four agents · one room"])
    for k in range(4):
        ev.append([ms(s1 + 0.6 + k * 0.72), "flash", k])
    # L2 Intake (first agent — no handoff)
    s2 = starts[2]
    ev += [[ms(s2 + 0.1), "activate", 0], [ms(s2 + 0.1), "plab", "extracting facts…"],
           [ms(s2 + durs[2] * 0.6), "art", "a0"], [ms(s2 + durs[2] * 0.6), "msg", 0]]
    # L3 Policy
    s3 = starts[3]
    ev += ho(0, 0, 1, s3)
    ev += [[ms(s3 + 0.12), "plab", "applying ruleset…"],
           [ms(s3 + durs[3] * 0.58), "art", "a1"], [ms(s3 + durs[3] * 0.58), "msg", 1]]
    # L4 Risk + AI/ML API
    s4 = starts[4]
    ev += ho(1, 1, 2, s4)
    ev += [[ms(s4 + 0.12), "aimlon", 0], [ms(s4 + 0.12), "plab", "scoring via AI/ML API…"],
           [ms(s4 + 1.1), "score", [88, int(durs[4] * 1000 * 0.62)]],
           [ms(s4 + durs[4] * 0.9), "aimloff", 0], [ms(s4 + durs[4] * 0.9), "msg", 2]]
    # L5 Counsel + re-loop
    s5 = starts[5]
    ev += ho(2, 2, 3, s5)
    ev += [[ms(s5 + 0.12), "plab", "reviewing…"],
           [ms(s5 + durs[5] * 0.5), "reloopon", 0], [ms(s5 + durs[5] * 0.5), "msg", 3]]
    # L6 Result + verdict
    s6 = starts[6]
    ev += [[ms(s6 + 0.1), "reloopoff", 0], [ms(s6 + 0.1), "plab", "finalizing memo…"],
           [ms(s6 + durs[6] * 0.52), "art", "a3"], [ms(s6 + durs[6] * 0.52), "msg", 4],
           [ms(s6 + durs[6] * 0.52), "finish", 3], [ms(s6 + durs[6] * 0.66), "verdict", 0],
           [ms(content_end + 0.45), "plab", "audit complete"]]
    ev = [e for e in ev if e[0] >= 0]
    ev.sort(key=lambda x: x[0])

    # assemble narration track: lead silence + clips spaced by gaps + tail
    parts = []
    filt = []
    parts += ["-f", "lavfi", "-t", f"{LEAD}", "-i", "anullsrc=r=44100:cl=stereo"]
    idx = 1
    seg_labels = ["0:a"]
    for i, wav in enumerate(clips):
        parts += ["-i", str(wav)]
        seg_labels.append(f"{idx}:a")
        idx += 1
        if i < len(clips) - 1:
            parts += ["-f", "lavfi", "-t", f"{GAP}", "-i", "anullsrc=r=44100:cl=stereo"]
            seg_labels.append(f"{idx}:a")
            idx += 1
    parts += ["-f", "lavfi", "-t", f"{TAIL}", "-i", "anullsrc=r=44100:cl=stereo"]
    seg_labels.append(f"{idx}:a")
    concat = "".join(f"[{l}]" for l in seg_labels) + f"concat=n={len(seg_labels)}:v=0:a=1[a]"
    vo = TMP / "vo.m4a"
    subprocess.run(["ffmpeg", "-y", *parts, "-filter_complex", concat,
                    "-map", "[a]", "-c:a", "aac", "-b:a", "160k", str(vo)],
                   capture_output=True, check=True)

    tpl = (HERE / "explainer_vo.html").read_text()
    built = tpl.replace("__EVENTS__", json.dumps(ev)).replace("__TOTAL__", str(total_ms))
    (HERE / "_vo_built.html").write_text(built)

    print(f"lines: {[round(d,2) for d in durs]}")
    print(f"total: {total_s:.2f}s  frames: {int(total_ms/DT)+1}")
    return total_ms, vo


def page_ws():
    for _ in range(50):
        try:
            data = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
            for t in data:
                if t.get("type") == "page":
                    return t["webSocketDebuggerUrl"]
        except Exception:
            pass
    raise RuntimeError("no page target")


class CDP:
    def __init__(self, ws):
        self.ws = ws; self._id = 0; self._p = {}; self._b = asyncio.Event()
    async def _read(self):
        async for raw in self.ws:
            m = json.loads(raw)
            if "id" in m and m["id"] in self._p:
                self._p.pop(m["id"]).set_result(m.get("result", {}))
            elif m.get("method") == "Emulation.virtualTimeBudgetExpired":
                self._b.set()
    async def send(self, method, **params):
        self._id += 1
        fut = asyncio.get_event_loop().create_future(); self._p[self._id] = fut
        await self.ws.send(json.dumps({"id": self._id, "method": method, "params": params}))
        return await fut
    async def advance(self, budget):
        self._b.clear()
        await self.send("Emulation.setVirtualTimePolicy", policy="advance", budget=budget,
                        maxVirtualTimeTaskStarvationCount=STARVATION)
        await self._b.wait()


async def capture(total_ms):
    FRAMES.mkdir(exist_ok=True)
    for f in FRAMES.glob("*.png"):
        f.unlink()
    n = int(total_ms / DT) + 1
    url = (HERE / "_vo_built.html").as_uri()
    async with websockets.connect(page_ws(), max_size=64 * 1024 * 1024) as ws:
        cdp = CDP(ws); reader = asyncio.create_task(cdp._read())
        await cdp.send("Page.enable")
        await cdp.send("Emulation.setDeviceMetricsOverride", width=W, height=H,
                       deviceScaleFactor=SCALE, mobile=False, screenWidth=W, screenHeight=H)
        await cdp.send("Emulation.setVirtualTimePolicy", policy="pause")
        await cdp.send("Page.navigate", url=url)
        cdp._b.clear()
        await cdp.send("Emulation.setVirtualTimePolicy", policy="pauseIfNetworkFetchesPending",
                       budget=320.0, maxVirtualTimeTaskStarvationCount=STARVATION)
        await cdp._b.wait()
        for i in range(n):
            await cdp.advance(DT)
            shot = await cdp.send("Page.captureScreenshot", format="png", fromSurface=True)
            (FRAMES / f"f{i:04d}.png").write_bytes(base64.b64decode(shot["data"]))
            if i % 90 == 0:
                print(f"frame {i}/{n}", flush=True)
        reader.cancel()
    return n


def main():
    total_ms, vo = build_audio_and_events()
    n = asyncio.run(capture(total_ms))
    out = HERE / "explainer_narrated.mp4"
    subprocess.run(["ffmpeg", "-y", "-framerate", str(FPS), "-i", str(FRAMES / "f%04d.png"),
                    "-i", str(vo), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                    "-preset", "slow", "-c:a", "aac", "-shortest", "-movflags", "+faststart",
                    str(out)], capture_output=True, check=True)
    print("WROTE", out, f"({n} frames)")


if __name__ == "__main__":
    main()
