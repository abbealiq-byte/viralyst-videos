# Storyboard format (for Claude)

One JSON file per video in `storyboards/`, named `YYYY-MM-DD_slug.json`. Pushing it triggers
GitHub Actions, which renders `videos/YYYY-MM-DD_slug.mp4` (public raw URL:
`https://raw.githubusercontent.com/abbealiq-byte/viralyst-videos/main/videos/<name>.mp4`).
Then schedule it in Metricool (blogId 7660307, YouTube short + TikTok, isAigc true).
Poll `GET /repos/abbealiq-byte/viralyst-videos/actions/runs?per_page=1` until completed.

Top level: `{"title": str, "speed": 1.1, "hide_brand_on_hook": true, "scenes": [...]}`.
Each scene: `say` (voice line, Kokoro af_jessica), `type`, optional `pause` (s after line),
`speed`, last scene `hold` (s). Scene lasts as long as its voice line. Colors: cyan, pink,
yellow, white, muted, grey. Lines: `[{"t": "TEXT", "color": "yellow", "size": 96, "pop": true, "at": 0.5}]`.

| type | fields |
|---|---|
| text | heading, lines, sub, crown (bool), y |
| quote | lines, by |
| counter | heading, top, prefix, value, decimals, suffix, label, sub, stopwatch (bool), color |
| dots | heading, total, cols, shape (cube/circle), highlight (n), highlight_color, count (bool), label, moon (bool) |
| list | heading, items[], highlight (index), crown, lines |
| ring | heading, total, count, center, crown, lines |
| stamps | heading, items [{t, color, at}], sub |
| bars | heading, items [{label, value, show, color}], sub |
| calendar | heading, month, day, color, lines |
| buttons | lines, options [2], sub, footer |
| icon | heading, icon (laptop/lock/shield/trophy/alarm), lines |
| stars | starfield background + text fields |
| curtain | theatre curtain opening + lines |

Recipe that works: hook first (most shocking line, no heading, brand hidden), tension in
the middle, payoff last, then a two-sided question with `buttons`. 25-40 s total.
