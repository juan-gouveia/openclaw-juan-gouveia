# Skills we're building

## Random Picture of the Day

1. What does this skill do? One sentence.
  - This skill requests a picture from the user and stores it on a designated folder.

2. What input does the agent need? What do you give it, in what format — and what does it already know from the five configuration files?
  - Agent needs to randomly select a time of day (between 09:00 and 21:00, Spain time) each day
  - Send a message using Telegram requesting the "Picture of the day"
  - Receive the picture
  - Rename the picture to "picoftheday - XXX"
  - Store it inside a previously designated Google Drive folder

3. What does a good output look like? Format, destination (a Doc, a Calendar event, a Telegram message…), and how you'll know it worked.
  - There's a picture properly renamed and stored corresponding to the current day
  - Agent should be able to list back existing pictures inside the folder

4. Implementation (2026-09-28) — `skills/picoftheday/`
  - Name format: `picoftheday - NNN - DD-MM-YY.jpg` (NNN from 001, next = highest in folder + 1), Drive folder "Pic of the Day" (upload via Zapier; listing via Drive API with the service account, folder shared as Viewer since 2026-10-01) MCP
  - `picoftheday-planner` automation (08:50 Europe/Madrid) picks a random time and creates a one-shot job that sends the request on Telegram
  - Upload uses the Telegram file URL (Zapier only accepts public URLs); token copy in secret store entry `TELEGRAM_BOT_TOKEN_FILES`


## Daily AI News

1. What does this skill do? One sentence.
  - Every morning and evening this skill collects the newest AI headlines from Wired and El País, writes them with their links into a Google Doc and sends the user the doc's link on Telegram.

2. What input does the agent need? What do you give it, in what format — and what does it already know from the five configuration files?
  - Sources (RSS read with `curl` one-liners given in SKILL.md; no `web_search` provider is configured):
    + El País: tag feed `https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/tag/inteligencia_artificial_a` (same news as https://elpais.com/noticias/inteligencia-artificial/)
    + Wired: https://es.wired.com/tag/inteligencia-artificial has no feed of its own, so use the general feed `https://es.wired.com/feed/rss` and keep only items whose `media:keywords` include "Inteligencia Artificial" (they match the tag page)
  - Maximum 6 news per run, maximum 3 per source, newest first
  - Only news published after the last review: the time in the doc's last "Actualizado:" line. First run (no doc yet): last 24 hours
  - Runs twice a day at 09:00 and 21:00 (Europe/Madrid)
  - Destination: Google Doc "Noticias diarias de IA" in the Drive root (written via Google Drive API with a service account since 2026-10-01, no Zapier)

3. What does a good output look like? Format, destination (a Doc, a Calendar event, a Telegram message…), and how you'll know it worked.
  - The doc "Noticias diarias de IA" (always the same file and link) is overwritten by the first run of the day: title, an "Actualizado: DD-MM-YYYY HH:MM (UTC+HH:MM)" line, and one section per source with its headlines as clickable links
  - Later runs the same day (21:00) append a block "Actualización de la noche" with its own "Actualizado" line and sections, keeping the morning news. The mode is decided by the date of the doc's first "Actualizado" line (today → append), not by the clock
  - If there is nothing new, the block is still written with a "Sin noticias nuevas" line, so the "Actualizado" time moves forward
  - A Telegram message to the user with the link to the doc and how many news it has
  - It worked if: the message arrives after 09:00, the doc shows today's "Actualizado" time, no headline repeats from the previous day, and the links open the articles

4. Implementation (2026-09-29) — `skills/noticias-ia/`, only `SKILL.md`, no scripts
  - (Superseded 2026-10-01: now curl + Drive API, no Zapier.) Zapier Google Docs actions called directly with `mcporter` (full path and config, as in Pic of the Day):
    1. `google_docs_find_a_document` by name; if there is no result, `google_docs_create_document_from_text` with placeholder text
    2. `google_docs_make_api_get_request` (read action; needs `method` and `fail_on_errors`) with `fields` limited to `endIndex` and the text: gives the last `endIndex` and the previous "Actualizado" time
    3. `google_docs_make_api_mutating_request`: `batchUpdate` with `deleteContentRange` from 1 to last `endIndex` − 1 (empties the doc)
    4. `google_docs_append_text_to_document` with the headlines as HTML (`<ul><li><a href>`)
  - Automation made with `openclaw cron add` at 09:00 Europe/Madrid, isolated session, `--announce --channel telegram` to the user's chat: the run's final text is the Telegram message
  - Steps 1–4 tested on 2026-09-29 with the test doc "PRUEBA Noticias OpenClaw": links clickable, old content fully replaced, same doc link
  - Automation `noticias-ia` created (daily 09:00 Europe/Madrid). Agent test runs on 2026-09-29 OK: doc created, 4 news picked correctly after the cutoff, final text is only the Telegram message
  - 2026-09-30: first scheduled run OK. Added the 21:00 pass (append mode, step 3 skipped); automation schedule changed to `0 9,21 * * *`

## MEGA keep-alive

1. What does this skill do? One sentence.
  - Every two months this skill logs in to each of the user's mega.nz accounts so MEGA doesn't close them for inactivity.

2. What input does the agent need? What do you give it, in what format — and what does it already know from the five configuration files?
  - One credentials file per account in `/root/.openclaw/credentials/mega/<label>.megarc` (`[Login]` / `Username =` / `Password =`), created by the user by hand; the label names the account in messages
  - Runs on day 1 of every odd month (Jan, Mar, May, Jul, Sep, Nov) at 10:00 Europe/Madrid

3. What does a good output look like? Format, destination (a Doc, a Calendar event, a Telegram message…), and how you'll know it worked.
  - All logins OK: nothing is sent (final text `NO_REPLY`); `state/last_ok_<label>` gets the date
  - Any login fails (after one retry 2 minutes later): a short Telegram message naming the failed accounts, the error with a hint, and a reminder to log in by hand on mega.nz
  - It worked if: no Telegram message, `last_ok_*` dates updated, and the account's "Sesiones" list on mega.nz shows the new session

4. Implementation (2026-10-09) — `skills/mega-keepalive/`, only `SKILL.md`, no scripts
  - `megatools df --config <file>` (logs in, reads the quota, exits). Uses the upstream static build 1.11.5 in `/opt/megatools` (link `/usr/local/bin/megatools`): the Ubuntu package 1.10.3 gets HTTP 402 because MEGA now requires a hashcash challenge at login
  - Accounts with 2FA can't log in with megatools (would need MEGAcmd)
  - Automation `mega-keepalive`: `0 10 1 */2 *` Europe/Madrid, isolated, announce to the user's Telegram chat; silence comes from the `NO_REPLY` final text
