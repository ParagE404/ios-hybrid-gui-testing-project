# Generative AI use log

| # | Date | Tool | Task | Key prompt(s) | Output used? | How I verified it | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | 2026-06-28 | Claude Code | Set up development environment: Python 3.12, Appium, and VLM model weight downloads | "Read setup-week1.md. Implement steps 2-4... record versions in docs/versions.md" | Accepted with modification: I manually handled Node version to avoid PATH conflicts | Verified via version commands and \`pytest\` | docs/versions.md |
| 2 | 2026-07-04 | Claude | Developed synthetic screen generator and ShowUI grounding/latency scripts | "Help me write a script to generate a synthetic labelled iOS screen and a batch script to score latency" | Accepted: I ran and tested the scripts on the Mac | Verified via result metrics in D-002 | spikes/out/showui_batch.json |
