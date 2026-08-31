---
name: cobalt
description: Download public videos via local cobalt.tools instance. Checks if server running, starts it if not. Use for yt/tiktok/etc.
---

# cobalt

`~/i/imput/cobalt` (api at `~/i/imput/cobalt/api`). Requires `API_URL=http://localhost:9000/` in `api/.env` and `pnpm install` once.

## check & start
```bash
curl -s http://localhost:9000/ >/dev/null || (cd ~/i/imput/cobalt/api && nohup pnpm start > /tmp/cobalt.log 2>&1 & sleep 4; curl -s http://localhost:9000/ >/dev/null && echo ok || echo fail)
```

## download
```bash
TUNNEL=$(curl -s -X POST http://localhost:9000/ -H "Accept: application/json" -H "Content-Type: application/json" -d '{"url":"<URL>","videoQuality":"720","youtubeVideoCodec":"h264"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['url'])")
curl -L -o out.mp4 "$TUNNEL"
# alt python fetch if curl fails, add youtubeHLS:true for SABR-blocked yt
```

yt fallback if tunnel gives 0 bytes (youtube SABR/challenge): `yt-dlp --remote-components ejs:github -f "bv*+ba/best" --downloader aria2c -o out.mp4 "<URL>"`
