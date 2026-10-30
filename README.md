# Viralyst videos

Faceless trend channel "Trends, explained". This repo renders the videos automatically.

- `storyboards/<date>_<slug>.json`: one file per video (scenes, voice lines, scene types).
- `engine/`: the render engine (Kokoro voice "af_jessica" + Viralyst style).
- `videos/`: finished MP4s. Metricool schedules them from their public raw links.

Push a new storyboard and GitHub Actions renders it into `videos/` within a few minutes.
