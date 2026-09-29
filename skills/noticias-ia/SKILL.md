---
name: noticias-ia
description: "Daily AI news: collect the newest AI headlines from Wired and El País and overwrite the Google Doc 'Noticias diarias de IA' (Drive root) with them via Zapier, then reply with the doc link. Use when the noticias-ia automation runs (09:00 Europe/Madrid) or when Juan asks for the AI news / noticias de IA."
metadata: { "openclaw": { "emoji": "📰", "requires": { "bins": ["curl"] } } }
---

# Noticias diarias de IA

Every day at 09:00 (Europe/Madrid) an automation runs this skill. Collect up to 6 AI headlines published since the last run (at most 3 from Wired and 3 from El País), write them into the Google Doc **Noticias diarias de IA** (Drive root, always the same file) and finish with a short message for Juan. The automation delivers your final text to Telegram, so don't send it yourself.

No scripts: everything is `curl` for the feeds and direct `mcporter` calls to Zapier. Do the steps in order and stop at the first error.

## Zapier calls

`mcporter` is not on the PATH. Always call it like this, with the JSON in a quoted heredoc so quotes and apostrophes in headlines can't break the shell:

```
/var/lib/openclaw/tools/node/npm/bin/mcporter --config /root/.openclaw/workspace/config/mcporter.json \
  call zapier.<TOOL> --no-oauth --args "$(cat <<'EOF'
{ ...json... }
EOF
)"
```

- `<TOOL>` is `execute_zapier_read_action` or `execute_zapier_write_action`, as given in each step.
- `"selected_api"` is always `"GoogleDocsV2CLIAPI"`.
- If the output says 401, "auth required" or OAuth, stop: Zapier must be re-authorized on the server with `mcporter auth zapier`. Report that as your final text.

## Steps

### 1. Find or create the doc

Read action, `"action":"document"`, `"tool_name":"google_docs_find_a_document"`, `"params":{"title":"Noticias diarias de IA"}`.

- If `results` has a document, keep its `id` (DOC_ID) and `alternateLink` (DOC_LINK).
- If `results` is empty, this is the first run. Create it with the write action `"action":"newtxtdocument"`, `"tool_name":"google_docs_create_document_from_text"`, `"params":{"title":"Noticias diarias de IA","file":"Noticias"}`, and keep `id` and `alternateLink` from the result. The new doc holds the placeholder text "Noticias": still do steps 2 and 4 so it gets deleted. The cutoff (step 2) is 24 hours ago.

### 2. Read the doc: end position and last review time

Read action, `"action":"_zap_raw_request"`, `"tool_name":"google_docs_make_api_get_request"`, params:

```
{"url":"https://docs.googleapis.com/v1/documents/DOC_ID","method":"GET","fail_on_errors":"true",
 "querystring":{"fields":"body.content(endIndex,paragraph(elements(textRun/content)))"}}
```

- END = the `endIndex` of the **last** element in `body.content`.
- CUTOFF = the date and time in the line that starts with `Actualizado:` (format `DD-MM-YYYY HH:MM (UTC+HH:MM)`). If there is no such line (doc just created), CUTOFF = 24 hours ago.
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

### 4. Empty the doc

Skip this step if END is 2 or less (doc already empty). Otherwise write action, `"action":"_zap_raw_request"`, `"tool_name":"google_docs_make_api_mutating_request"`, params (END − 1 as a number):

```
{"url":"https://docs.googleapis.com/v1/documents/DOC_ID:batchUpdate","method":"POST","fail_on_errors":"true",
 "body":"{\"requests\":[{\"deleteContentRange\":{\"range\":{\"startIndex\":1,\"endIndex\":END_MINUS_1}}}]}"}
```

The result must have `"status": 200`.

### 5. Write the news

Write action, `"action":"append"`, `"tool_name":"google_docs_append_text_to_document"`, `"params":{"file":"DOC_ID","newline":"false","text":"<HTML>"}`. The HTML (escape `"` as `\"` inside the JSON string):

```
<h1>Noticias diarias de IA</h1>
<p><i>Actualizado: 30-09-2026 09:00 (UTC+02:00)</i></p>
<h2>Wired</h2>
<ul><li><a href="LINK">TITLE</a></li> ...</ul>
<h2>El País</h2>
<ul><li><a href="LINK">TITLE</a></li> ...</ul>
```

- A source with no new items gets `<p>Sin noticias nuevas.</p>` instead of the list; a failed feed gets `<p>No se pudo consultar la fuente.</p>`.
- Always write the doc, even with no news at all, so the `Actualizado` time moves forward.

### 6. Final text (goes to Juan on Telegram)

Your final reply is sent to Juan as it is, so it must be **only** this message: no progress notes, step names or comments before or after it. Short, in Spanish, no headers:

```
📰 Noticias diarias de IA: N nuevas (Wired X, El País Y)
DOC_LINK
```

With no news: `📰 Hoy no hay noticias nuevas de IA.` plus the link. If a step failed, say which step and the error in one or two lines; if the doc was already emptied (step 4) and step 5 failed, say so, because the doc is empty until the next run.

## Automation

The `noticias-ia` automation (`openclaw cron list`) runs daily at 09:00 Europe/Madrid in an isolated session and delivers the final text to Juan's Telegram chat. If Juan asks for the news at another time, run the same steps; the next automated run will only pick up news published after that.
