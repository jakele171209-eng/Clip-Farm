# Clip Farm

Finds the moments in a stream where chat goes wild, then cuts them into vertical 9:16 clips with big captions, ready for Shorts and TikTok.

Only clip streamers you have permission for: a paid clipping campaign (Whop Content Rewards, Vyro) or a written OK from the streamer. Crediting the streamer is not permission.

## How it works

Chat is a crowd noise meter. Every second of the stream gets a hype score from how many messages arrive and how many contain hype words (KEKW, OMEGALUL, W, CLIP IT, 💀...). Each second is compared with the normal noise level around it, so busy and quiet chats are judged fairly. The loudest separated peaks become clips, starting 20 seconds before the peak, because chat reacts a few seconds after the action.

## Setup (Windows, macOS or Linux)

1. Install Python 3.11+ and [FFmpeg](https://ffmpeg.org/download.html).
2. `pip install -r requirements.txt`
3. Download [TwitchDownloaderCLI](https://github.com/lay295/TwitchDownloader/releases) for chat replays.

## Use

```bash
# 1. Get the stream replay and its chat (Twitch VOD id from the URL twitch.tv/videos/<id>)
yt-dlp -o vods/vod.mp4 https://www.twitch.tv/videos/<id>
TwitchDownloaderCLI chatdownload --id <id> -o chat.json

# 2. Find the top moments
python -m clipfarm find --chat chat.json --top 10 --out moments.json

# 3. Cut them as vertical clips with captions
python -m clipfarm cut --video vods/vod.mp4 --moments moments.json --outdir clips --captions
```

Tune with `--pre` / `--post` (seconds before and after the peak), `--gap` (minimum seconds between clips) and `--min-score` (higher = only bigger spikes).

## Tests

```bash
python -m pytest -q
```

## Roadmap

- [x] Chat spike finder
- [x] Vertical cutter with burned-in captions
- [ ] Claude ranks moments using the transcript and writes titles
- [ ] Review page to approve or reject clips
- [ ] YouTube upload (private) and TikTok drafts via OAuth
- [ ] Analytics loop
