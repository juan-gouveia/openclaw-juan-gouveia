---
name: picoftheday
description: "Picture of the Day: Juan's daily photo, stored in Google Drive ('Pic of the Day'): the upload goes through Zapier, listing goes through the Drive API. Use when Juan sends a photo on Telegram while today's picture is pending, when he says it's the picture/pic/foto of the day, or asks to list/see stored pictures of the day."
metadata: { "openclaw": { "emoji": "📸", "requires": { "bins": ["python3"] } } }
---

# Picture of the Day

Every day at a random time between 09:00 and 21:00 (Europe/Madrid), an automation asks Juan on Telegram for his "Picture of the Day". When he answers with a photo, store it in Google Drive, folder **Pic of the Day**, named `picoftheday - NNN - DD-MM-YY` (NNN = running number from 001, e.g. `picoftheday - 001 - 28-09-26.jpg`).

Everything goes through the helper script. Never build Telegram file URLs or call Zapier by hand: the URL contains the bot token, and the script keeps it out of your output.

```
python3 {baseDir}/scripts/pod.py <status|upload [--force]|list|flush|schedule|request>
```

## When Juan sends a photo

1. Run `pod.py status`.
2. If `status` is `pending` or `scheduled`, or Juan says it's the picture of the day, run `pod.py upload`.
3. Handle the result:
   - `uploaded`: confirm to Juan with the file name and Drive link.
   - `queued`: Zapier failed (e.g. task limit exceeded), so the photo was saved in a local queue and will be uploaded automatically when Zapier works again (the daily `schedule` run and every new upload retry it). Tell Juan it is queued, not lost; don't retry by hand and don't use `--force`.
   - Exit code 3 / `exists`: today's picture is already stored. Ask Juan whether to add this one too. Only if he says yes, run `pod.py upload --force` (it gets the next number).
   - "La última foto es del …": the newest photo is not from today. Ask Juan before using `--force`.
   - Any other error: tell Juan the upload failed and why. The photo stays in Telegram and locally, so it can be retried.
4. If `status` is `done` or `none` and Juan didn't mention the picture of the day, don't upload. The photo is probably for something else.

## When Juan asks for the stored pictures

Run `pod.py list` and reply with one bullet per picture: date and link, newest first. Entries with `"queued": true` have no link yet: list them as "pendiente de subir". No headers on Telegram; use **bold** if needed.

## Scheduling (already automated)

- The `picoftheday-planner` automation runs `pod.py schedule` daily at 08:50 Europe/Madrid. It creates a one-shot `picoftheday-request-<date>` job at a random time. That job runs `pod.py request`, which marks the day `pending` and sends the request message to Telegram.
- Days that end without a photo are marked `missed` the next morning. There are no reminders.
- If Juan asks to be asked now, run `pod.py request` and send him its output.

## Files

- `config.json`: Drive folder, chat id, time window, name pattern, the name of the token entry in the secret store.
- Listing (`status`/duplicate guard/`list`) uses the Google service account in `/root/.openclaw/credentials/google-sa.json`; the Drive folder must stay shared with its `client_email` as Viewer. If `pod.py` says it cannot read the folder, that sharing was removed. The service account has no Drive quota, so the upload itself still goes through Zapier.
- Queue: `queue_dir` in `config.json` (`/root/.openclaw/picoftheday-queue/`, outside the repo) holds `queue.json` and a local copy of each photo. `pod.py flush` uploads the queue manually; photos get their number at upload time, in order. Day status is `queued` until uploaded.
- `state.json`: per-day status (`scheduled`, `pending`, `done`, `missed`). Local only, git-ignored.
- The bot token is read from the env-kind secret-store entry `TELEGRAM_BOT_TOKEN_FILES`. If Juan revokes the token in BotFather, both `TELEGRAM_BOT_TOKEN` and this entry must be updated.
