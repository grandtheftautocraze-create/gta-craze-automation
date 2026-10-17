# Chat-to-PC connection

## Install once
Download this repository ZIP, extract it, and double-click `install-connection.cmd`.
It locates the existing production folder at `C:\GTA-Craze\gta-craze-automation-main`
(or asks you to select it). It installs only the bridge worker into that existing
folder and registers `GTA Craze Chat Bridge` under the signed-in Windows user.
Existing video schedules are retained. The PC must be awake, online and signed in.

The installer opens GitHub's fine-grained token page. Select the owner
`grandtheftautocraze-create`, **Only select repositories**, `gta-craze-automation`,
and repository **Contents: Read and write**. Pick an expiration you will renew.
Paste the token only into the installer's hidden local prompt, never into chat.
It is saved as a Windows-user-encrypted SecureString in `data/bridge-token.xml`.
The token permits repo content changes, so restrict it to this repository.
No inbound ports or remote desktop access are enabled.

The verify step checks both GitHub reads and writes. It does not generate a video.
Once the installer succeeds, ask ChatGPT to queue a ping and inspect its result.
Windows registration, token decryption and a real video job require validation on
the user's Windows computer; Linux unit tests do not establish that installation
has succeeded.

## Chat operator instructions
Use the connected GitHub tools to read `bridge/queue.json` and its latest blob SHA.
Append a request, preserving pending entries, then update the file with that SHA.
Never include shell commands, credentials, machine paths, code, arbitrary URLs or
unrequested video topics. The worker supports only the two existing formats.

Request schema (all dates must have an explicit UTC offset):

```json
{
  "id": "unique-lowercase-request-id",
  "action": "generate_upload",
  "format": "community",
  "created_at": "CURRENT_UTC_TIME",
  "expires_at": "UP_TO_24_HOURS_LATER"
}
```

`action` is `ping` or `generate_upload`. `format` is `community` or `explainer`
for generation. A ping has no API generation costs and makes no YouTube upload.
Create requests AFTER installation; pre-installation requests are ignored.
Use the actual current timestamp when queuing. Keep at most 50 queue entries;
remove completed/expired entries as needed after reading status.

Read `bridge/status.json` after the next poll (up to two minutes, longer if the PC
is busy or asleep). `pong` proves the PC processed that request. `uploaded` with a
video URL confirms the runner received the upload response. `verified` alone only
means the installer or worker successfully accessed GitHub; it is not a live
heartbeat. No continuous monitoring exists in the chat between turns.

Generation invokes the existing installed `automation.py run --format FORMAT`
with the same OpenAI, footage and YouTube configuration. It requires publish/public.
No production program is automatically updated from GitHub. Updates still require
local installation. Only format selection is supported, not arbitrary topic prompts.

The bridge allows at most six remote generation attempts per rolling 24 hours,
in addition to scheduled runs. All runs share the existing monthly attempt cap.
Each request is claimed durably before work; interrupted or ambiguous uploads are
never retried automatically. `needs_review` requires local logs and YouTube Studio
reconciliation. Do not queue an identical replacement to bypass this guard.

Status in the repository contains only request IDs, state, timestamps and any
confirmed public video URL. In a public repo anyone can read those fields. Credentials,
narration, file paths, and detailed logs stay on the PC. Local logs are under `data/`.

## Disconnect / renew
Disable `GTA Craze Chat Bridge` in Windows Task Scheduler and revoke the GitHub token.
The daily video schedule is separate. To renew a token, wait until no bridge job is
running, remove `data/bridge-token.xml` in File Explorer, then rerun the installer.
Keep `data/bridge-state.json`; deleting it discards the duplicate-request history.
