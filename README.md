# GTA Craze — Windows Shorts automation

Local production runner for English GTA news, explained details and clearly fictional gameplay stories. No Render service required. This is a configurable first implementation, **not an activated or fully unattended channel**.

## What is implemented

- Research using OpenAI web search restricted to Rockstar domains, with source links saved.
- Original scripts and AI voiceover; a five-run rotation of news/details/story/news/details.
- FFmpeg 1080×1920 video rendering, five-word captions and normalized narration.
- Local SQLite job history, monthly attempt cap, process lock and upload-intent records.
- Direct YouTube OAuth upload with an exact channel-ID check and private visibility by default.
- Optional Windows scheduled task: Monday, Wednesday and Friday, 8 PM Windows local time.

## What still needs setup

1. OpenAI API billing/key (separate from ChatGPT subscriptions).
2. Licensed gameplay files and permission records. **No footage is bundled or automatically acquired.** A creator's permission must cover your use; keep evidence. The program trusts your catalog rather than independently verifying licenses. Do not label random downloaded clips as permitted.
3. A Google OAuth desktop client and one-time authorization to GTA Craze.
4. A real end-to-end private test on your Windows computer before enabling public uploads.

Metricool remains useful through ChatGPT, but its chat connection does not give this program an API credential. This implementation uploads directly to YouTube to avoid assuming Metricool API access. No cloud infrastructure or services are created.

## 1. Download and install

On this repository page choose **Code → Download ZIP**, then extract it into a permanent folder such as `C:\GTA-Craze`. Install Python 3.11+ from https://www.python.org/downloads/windows/ (include the Python launcher). Install a Windows FFmpeg build linked from https://ffmpeg.org/download.html and add its `bin` folder to your PATH. Open a new terminal and confirm `ffmpeg -version` and `ffprobe -version` work.

Double-click `setup.cmd`. It creates a local Python environment, installs requirements and reports missing settings. No paid API requests are made by setup or doctor. Package dependencies use bounded version ranges; a lockfile should be generated after the Windows pilot succeeds.

## 2. Credentials — keep these on your PC

Open `.env` in Notepad and put your OpenAI API key after `OPENAI_API_KEY=`. Create a key at https://platform.openai.com/api-keys and configure billing/usage limits in your account. Never paste keys in GitHub, chat, screenshots or README files.

In https://console.cloud.google.com/ create/select a project, enable **YouTube Data API v3**, configure the OAuth consent screen, and create an OAuth client of type **Desktop app**. For testing, add your Google account as a test user. Download the client JSON into this folder as `client_secret.json`. Testing-mode consent or Google account policy can require reauthorization; confirm long-term access before unattended operation.

Open a terminal in the project folder and run:

```powershell
.\.venv\Scripts\python.exe automation.py login
```

Sign in to the Google account that owns GTA Craze and select that channel. The program verifies channel ID `UCfXJFtnwFyBIhSQlQCSyPrA`, obtained from the user's Metricool connection. It refuses other channels. The OAuth token is stored locally under `data/`.

## 3. Footage

Obtain an initial collection of licensed GTA gameplay and place it in `media/`. Copy `media.example.json` to `media.json`. Add entries with accurate footage descriptions, exact credits and permission references; only set `permission_confirmed` to true once you have confirmed permission. Use short, relevant sequences; the renderer loops a clip if necessary. It preserves the whole frame with padding rather than cutting off gameplay. Original gameplay audio/music is removed.

This is the remaining sourcing dependency: the code cannot manufacture a creator's permission. There is no arbitrary YouTube downloader. Automated visual event detection, scene-by-scene editing and footage purchase are not implemented. Stories are generated from your descriptions and labeled fictional.

## 4. Generate a draft

```powershell
.\.venv\Scripts\python.exe automation.py doctor
.\.venv\Scripts\python.exe automation.py run
```

`config.json` defaults to `mode: draft` and `privacy: private`. Draft generation uses paid OpenAI calls, but does not upload. Inspect `data/<job-id>/video.mp4`, `script.json` and `captions.ass`. Captions use estimated word timings, not forced alignment; review their timing in the pilot. Text/voice models can be changed in config if unavailable to your API account.

News generation can intentionally stop if evidence is insufficient. A model's judgment and citation presence are **not a guarantee of factual accuracy**. Verify the first videos and periodically review later ones. There is no earnings/monetization guarantee.

## 5. Test a private upload, then enable automatic publishing

Set `mode` to `publish` while keeping `privacy` set to `private` and upload an existing draft:

```powershell
.\.venv\Scripts\python.exe automation.py upload --job YOUR_JOB_ID
```

Check the private video in YouTube Studio. Upload behavior can depend on current Google project/account restrictions; verify before relying on public publishing. To publish future runs publicly, explicitly change `privacy` to `public`. General-audience GTA content is configured as not made for kids. Narration is disclosed as AI-generated in descriptions. Reassess metadata if your content changes.

A failed upload is never blindly retried. If a job says `uploading`, inspect YouTube Studio first: the server may have received it even if the response was lost. Do not delete the database to force a retry. A maintainer must reconcile its state with the uploaded video ID.

## 6. Schedule on your PC

After the private test succeeds, run the following in PowerShell from the folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-schedule.ps1
```

This registers one task under your current Windows user; it runs only while you are signed in. Screen locking is fine. The task attempts to wake the machine, but firmware/power settings may prevent wakeup. Leave it awake with internet for reliable operation. Set Windows to Pakistan time for the intended schedule. Logs are in `data/runner.log`. Missed runs may execute on the next available opportunity. No automatic retries are registered.

To stop:

```powershell
Unregister-ScheduledTask -TaskName 'GTA Craze Production' -Confirm:$false
```

## Cost controls and limits

The starting limit is **12 generation attempts per UTC calendar month**, including failed/held attempts. This is a volume limit, **not a guaranteed PKR 10,000 spending cap**. Provider prices, model choice, search usage, taxes, exchange rates and footage costs affect actual spend. Check provider billing after the pilot, set account-side controls and adjust the attempt cap. No purchases are made by installing this project.

There is no automated channel analytics optimization or comment moderation yet. Use Metricool with ChatGPT for analysis. Long-term unattended sourcing and editorial quality still require work; do not treat this first runner as a fully managed channel.

## Verification

`python -m unittest -v` tests permission gating, failed-attempt accounting, fiction disclosure and caption escaping. A synthetic local FFmpeg render can verify the rendering path without API calls. Live OpenAI generation, Google authorization, public uploading and Windows Task Scheduler must be tested on the user's PC. No live video has been uploaded during development.

## Implementation references

- https://developers.openai.com/api/docs/guides/tools-web-search
- https://developers.openai.com/api/docs/guides/text-to-speech
- https://developers.google.com/youtube/data/reference/rest/v3/videos/insert
- https://github.com/youtube/api-samples/blob/master/python/upload_video.py

## Automatic approved footage

Install updated requirements, then run `python automation.py fetch-footage` to
check and download the approved video without using OpenAI credits or uploading.
`run` now performs this step automatically too. `footage-sources.json` contains
one user-approved source and the permission statement supplied by the user.
The downloader checks that statement against the live description on first download,
saves the description and permission record, caches up to 1080p MP4 video, and
creates silent 60-second excerpts between the supplied chapter boundaries.
It preserves manual catalog entries and reuses cached files on later runs.
The default Windows FFmpeg directory C:\ffmpeg\bin is detected automatically.

This is timestamp clipping, not visual scene understanding. Creator claims are
not research evidence; scripts still use the existing Rockstar research workflow.
No live download or production upload was verified in the development environment.
YouTube may require a supported JavaScript runtime such as Deno, or reject a
request; the program stops rather than bypassing sign-in/access restrictions.
Install Deno if yt-dlp reports a missing JavaScript runtime. Keep yt-dlp current.
Cached permission is not a rights guarantee for third-party material in a video.

## Hands-off scheduled publishing

The runner can search the YouTube Data API for new GTA videos explicitly marked
Creative Commons, verify `status.license=creativeCommon`, download and cache up
to six minutes of silent gameplay, and add required attribution. It waits until
all current excerpts have been used once before looking for another source.
The scheduler runs the complete research, script, voice, edit, and upload flow.
The current configuration is `publish` / `public`; each scheduled success uploads
publicly. The computer must stay on, connected, and signed into the same Windows
account. Install the scheduled task once with PowerShell and `install-schedule.ps1`.
API calls can fail; no system can guarantee accurate research, a clean copyright
status, or engagement. The system does not yet moderate comments or make analytics
changes. YouTube API search for CC is the license filter; this cannot independently
prove that every uploader controls every embedded asset. The code strips original
audio, credits the source, and keeps a log. Review Studio notices when available.


## Short-form style

Scripts now open directly on a specific curiosity hook, explain one idea in a few
short beats, and land on a payoff. The voice uses the Coral preset with direction
for a warm, energetic gaming storyteller. The edit uses a blurred vertical backdrop,
a clear gameplay panel, subtle motion, and timed high-contrast captions. These are
original format choices informed by GTA TV Official Channel's fast detail/news
hooks; narration and wording are not copied. The renderer still uses the same
approved footage source throughout a Short, so it does not yet select scenes to
match individual sentences.
