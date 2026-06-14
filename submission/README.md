# HireGuard — Submission Assets

Visual assets for the Band of Agents Hackathon submission.

| File | What it is | How to use |
|---|---|---|
| `cover.png` | 2560×1440 cover image (16:9) | Upload as the submission cover/thumbnail |
| `cover.html` | Source for the cover | Edit + re-render if you want changes |
| `deck.pdf` | 9-slide presentation (1280×720) | Upload as the slide deck |
| `deck.html` | Source for the deck | Edit + re-render |
| `explainer_narrated.mp4` | **The video** — 1920×1080, 30fps, ~46s, with voiceover | Upload as the demo video |
| `explainer.mp4` | Silent version — 1920×1080, ~17.6s, one clean loop | Alt / B-roll |
| `explainer_loop3.mp4` | Silent loop ×3 (~53s) | Alt longer fill |
| `explainer.html` | Source for the silent loop | Edit, then re-render (below) |
| `explainer_vo.html` | Source for the narrated version (timeline injected at build) | Edit copy/visuals |
| `render_narrated.py` | Build script for the narrated MP4 (TTS + sync + capture + mux) | Re-run to rebuild |

## The narration

Voiced with macOS `say` (voice: Samantha). Each line cues the matching agent on screen:

1. "Every job posting is a legal minefield: federal discrimination law, plus a patchwork of state pay-transparency rules."
2. "HireGuard audits it with a team of four AI agents, collaborating live in a Band room." *(cards sweep in)*
3. "First, Intake reads the hiring packet and extracts the facts."
4. "PolicyAgent applies the compliance ruleset and cites every candidate violation."
5. "RiskScorer sends each finding to the AI/ML API, scoring its legal exposure from zero to one hundred."
6. "Then Counsel reviews the case, and can bounce a weak finding back to PolicyAgent for another look."
7. "The result: a defensible, cited audit memo. Verdict, high. Ready for human sign-off."

To rebuild the narrated video (edit the lines in `render_narrated.py` first if needed):

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --remote-debugging-port=9222 \
  --user-data-dir=/tmp/hg_chrome_profile2 about:blank &
python render_narrated.py     # → explainer_narrated.mp4
```

Want a different voice? `say -v '?'` lists them; change `VOICE` in `render_narrated.py`.

## Re-rendering the video from explainer.html

The MP4 is captured deterministically from `explainer.html` with Chrome's virtual
clock (smooth, frame-exact) and assembled with ffmpeg. After editing the HTML,
re-run the capture script in this folder:

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --remote-debugging-port=9222 \
  --user-data-dir=/tmp/hg_chrome_profile about:blank &
python _capture.py            # writes _frames/  (script regenerated on demand)
ffmpeg -y -framerate 30 -i _frames/f%04d.png -f lavfi \
  -i anullsrc=channel_layout=stereo:sample_rate=44100 \
  -c:v libx264 -pix_fmt yuv420p -crf 18 -preset slow -c:a aac -shortest \
  -movflags +faststart explainer.mp4
```

The scene shows: packet → @Intake → @PolicyAgent → @RiskScorer scoring via the
AI/ML API → @Counsel bounces a thin Critical back (the re-loop) → VERDICT: HIGH,
with a synced Band room log and progress bar.

## Re-rendering after edits

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# cover → PNG (2x)
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
  --window-size=1280,720 --virtual-time-budget=2500 \
  --screenshot="cover.png" "file://$PWD/cover.html"

# deck → PDF
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=4000 \
  --print-to-pdf="deck.pdf" "file://$PWD/deck.html"
```

All three share one identity: dark legal-tech, teal `#5EEAD4` brand accent, severity palette (Critical red / Risk amber / Gap blue), Space Grotesk + Inter + JetBrains Mono.
