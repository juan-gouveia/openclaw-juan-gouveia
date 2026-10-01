---
name: noticias-ia
description: "Daily AI news: collect the newest AI headlines from Wired and El País into the Google Doc 'Noticias diarias de IA' (Drive root) via the Google Drive API — the first run of the day replaces the doc, later runs append a block — then reply with the doc link. Use when the noticias-ia automation runs (09:00 and 21:00 Europe/Madrid) or when Juan asks for the AI news / noticias de IA."
metadata: { "openclaw": { "emoji": "📰", "requires": { "bins": ["curl", "openssl"] } } }
---

# Noticias diarias de IA

Every day at 09:00 and 21:00 (Europe/Madrid) an automation runs this skill. Collect up to 6 AI headlines published since the last run (at most 3 from Wired and 3 from El País), write them into the Google Doc **Noticias diarias de IA** (Drive root, always the same file) and finish with a short message for Juan. The first run of the day (**new day** mode) replaces the whole doc; any later run that day (**append** mode) adds a new block at the end and leaves the earlier news untouched. The automation delivers your final text to Telegram, so don't send it yourself.

No scripts and no Zapier: everything is `curl` and `openssl`. The doc is written with one upload to the Google Drive API using a service account. Do the steps in order and stop at the first error.

Local files in `/root/.openclaw/workspace/skills/noticias-ia/state/` (git-ignored, never delete them): `hoy.html` is the full HTML currently in the doc (the source of truth for mode and cutoff), `token` is the short-lived Google access token. Never print the contents of `/root/.openclaw/.env`, `/root/.openclaw/credentials/` or `state/token`.

## Steps

### 1. Doc id and Google token

The doc id is the line `NOTICIAS_IA_DOC_ID=...` in `/root/.openclaw/.env`. Read only that line:

```
grep '^NOTICIAS_IA_DOC_ID=' /root/.openclaw/.env | cut -d= -f2-
```

- DOC_ID = the printed value. DOC_LINK = `https://docs.google.com/document/d/DOC_ID/edit`

Get an access token (valid 1 hour, written to `state/token`). Run this block exactly as written, once per run; it must print `token-ok`:

```
SA=/root/.openclaw/credentials/google-sa.json
b64u() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }
NOW=$(date +%s)
H=$(printf '{"alg":"RS256","typ":"JWT"}' | b64u)
C=$(printf '{"iss":"%s","scope":"https://www.googleapis.com/auth/drive","aud":"https://oauth2.googleapis.com/token","iat":%s,"exp":%s}' "$(grep '"client_email"' $SA | sed -E 's/.*: *"([^"]*)".*/\1/')" $NOW $((NOW+3600)) | b64u)
grep '"private_key"' $SA | sed -E 's/.*: *"//; s/",? *$//' | sed 's/\\n/\n/g' > /tmp/sa_key_nw.pem
S=$(printf '%s.%s' "$H" "$C" | openssl dgst -sha256 -sign /tmp/sa_key_nw.pem | b64u)
rm -f /tmp/sa_key_nw.pem
curl -s -d grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer -d "assertion=$H.$C.$S" https://oauth2.googleapis.com/token | grep -o '"access_token": *"[^"]*"' | sed -E 's/.*: *"([^"]*)"/\1/' > /root/.openclaw/workspace/skills/noticias-ia/state/token
chmod 600 /root/.openclaw/workspace/skills/noticias-ia/state/token; test -s /root/.openclaw/workspace/skills/noticias-ia/state/token && echo token-ok || echo token-FAILED
```

If it prints `token-FAILED` or the line `NOTICIAS_IA_DOC_ID` is missing, stop and report it as your final text (the service account key in `credentials/google-sa.json` or the Google project needs attention).

### 2. Mode and cutoff (from the local copy, no network)

Read `state/hoy.html`. If it does not exist (first run ever), MODE = **new day** and CUTOFF = 24 hours ago.

- Lines like `<p><i>Actualizado: DD-MM-YYYY HH:MM (UTC+HH:MM)</i></p>` mark each run today. There can be several.
- CUTOFF = the date and time in the **last** `Actualizado:` line.
- MODE: if the **first** `Actualizado:` line has today's date (`TZ=Europe/Madrid date '+%d-%m-%Y'`), MODE = **append**. Otherwise MODE = **new day**. Decide by that date, never by the clock time.
- Note the current time for the new line: `TZ=Europe/Madrid date '+%d-%m-%Y %H:%M (UTC%:z)'`.

### 3. Collect the news

Run these two commands exactly as written. Each prints one line per AI news item, newest first: `pubDate | title | link`. Don't read the raw feeds yourself: they are long and items get missed.

**Wired** (general feed, filtered to items tagged `Inteligencia Artificial`):

```
curl -sL -m 30 -A "Mozilla/5.0" https://es.wired.com/feed/rss | tr '\n' ' ' | sed 's#</item>#</item>\n#g' | grep 'Inteligencia Artificial' | sed -E 's#.*<title>([^<]*)</title>.*<link>([^<]*)</link>.*<pubDate>([^<]*)</pubDate>.*#\3 | \1 | \2#' | head -10
```

**El País** (AI tag feed):

```
curl -sL -m 30 -A "Mozilla/5.0" https://feeds.elpais.com/mrss-s/list/ep/site/elpais.com/tag/inteligencia_artificial_a | tr '\n' ' ' | sed 's#</item>#</item>\n#g' | grep '<item>' | sed -E 's#.*<title>([^<]*)</title>.*<pubDate>([^<]*)</pubDate>.*<link>([^<]*)</link>.*#\2 | \1 | \3#' | head -10
```

For each source, go down the list from the top and take the first items whose `pubDate` is later than CUTOFF, at most 3. `pubDate` is in GMT (+0000) and CUTOFF in Madrid time: convert before comparing. Stop at the first item that is not later than CUTOFF. Use titles and links exactly as printed; never invent, shorten or skip one. If a command prints nothing, write that source as unavailable and continue with the other.

### 4. Write the new block

Write this block to `state/bloque.html` with a quoted heredoc (`cat > .../state/bloque.html <<'EOF'`), so quotes and `$` in headlines can't break the shell. HTML-escape `&` as `&amp;` and `<` / `>` in titles; keep the links as printed (escape `&` in them too).

**New day** mode:

```
<h1>Noticias diarias de IA</h1>
<p><i>Actualizado: 30-09-2026 09:00 (UTC+02:00)</i></p>
<h2>Wired</h2>
<ul><li><a href="LINK">TITLE</a></li> ...</ul>
<h2>El País</h2>
<ul><li><a href="LINK">TITLE</a></li> ...</ul>
```

**Append** mode: the same, except the first line. Use `<h1>Actualización de la noche</h1>` if the current time is 20:00 or later, otherwise `<h1>Actualización de las HH:MM</h1>` with the current time:

```
<h1>Actualización de la noche</h1>
<p><i>Actualizado: 30-09-2026 21:00 (UTC+02:00)</i></p>
<h2>Wired</h2>
...
```

- A source with no new items gets `<p>Sin noticias nuevas.</p>` instead of the list; a failed feed gets `<p>No se pudo consultar la fuente.</p>`.
- Always write the doc, even with no news at all, so the `Actualizado` time moves forward.

### 5. Upload to the doc

Build the full page in `state/nuevo.html`: in **new day** mode it is `bloque.html` alone; in **append** mode it is `hoy.html` followed by `bloque.html` (`cat hoy.html bloque.html > nuevo.html`). Then replace the doc content with a single upload (the doc keeps its id and link) and, only if Google answers 200, make it the new local copy:

```
cd /root/.openclaw/workspace/skills/noticias-ia/state
DOC_ID=$(grep '^NOTICIAS_IA_DOC_ID=' /root/.openclaw/.env | cut -d= -f2-)
CODE=$(curl -s -o resp.json -w '%{http_code}' -X PATCH -H "Authorization: Bearer $(cat token)" -H 'Content-Type: text/html; charset=UTF-8' --data-binary @nuevo.html "https://www.googleapis.com/upload/drive/v3/files/$DOC_ID?uploadType=media&fields=id")
echo "http $CODE"; if [ "$CODE" = 200 ]; then mv nuevo.html hoy.html; else head -c 400 resp.json; fi
```

- `http 200` = done. The doc was replaced in one piece, so a failure never leaves it half-written or empty and `hoy.html` stays as it was.
- `http 404` or `403`: the doc was deleted or is no longer shared with the service account. Stop and report that (the doc must be shared as Editor with the `client_email` in `credentials/google-sa.json`; the service account cannot create files, it has no Drive quota).
- `http 401`: repeat step 1 once and retry.

### 6. Final text (goes to Juan on Telegram)

Your final reply is sent to Juan as it is, so it must be **only** this message: no progress notes, step names or comments before or after it. Short, in Spanish, no headers:

```
📰 Noticias diarias de IA: N nuevas (Wired X, El País Y)
DOC_LINK
```

With no news: `📰 Hoy no hay noticias nuevas de IA.` plus the link.

In **append** mode, the first line is `📰 Noticias de IA (actualización de la noche): N nuevas (Wired X, El País Y)` (or `(actualización de las HH:MM)` before 20:00); with no news, `📰 Esta noche no hay noticias nuevas de IA.` (before 20:00: `📰 No hay noticias nuevas de IA desde la última actualización.`) plus the link. If a step failed, say which step and the error in one or two lines (never include tokens or keys); the doc keeps its previous content.

## Automation

The `noticias-ia` automation (`openclaw cron list`) runs daily at 09:00 and 21:00 Europe/Madrid in an isolated session and delivers the final text to Juan's Telegram chat. If Juan asks for the news at another time, run the same steps (the mode comes from `state/hoy.html`, so a run in the middle of the day appends a block); the next automated run will only pick up news published after that.
