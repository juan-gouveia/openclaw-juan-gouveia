---
name: mega-keepalive
description: "MEGA keep-alive: log in to every configured mega.nz account so MEGA doesn't close them for inactivity. Silent (NO_REPLY) when every login works; a short Telegram warning for Juan naming the accounts that failed. Use when the mega-keepalive automation runs (day 1 of every odd month, 10:00 Europe/Madrid) or when Juan asks to log in to / check his MEGA accounts."
metadata: { "openclaw": { "emoji": "🔑", "requires": { "bins": ["megatools"] } } }
---

# MEGA keep-alive

Every two months an automation runs this skill. Log in once to each MEGA account configured on this server (that login is what counts as activity for mega.nz) and finish with the final text described in step 4. The automation delivers your final text to Telegram, so don't send it yourself.

No scripts: everything is the `megatools` CLI (1.11.5 static build in `/opt/megatools`, linked at `/usr/local/bin/megatools`; the old Ubuntu 1.10 package can't log in any more because MEGA now requires a hashcash challenge). Do the steps in order.

Accounts: one file per account in `/root/.openclaw/credentials/mega/`, named `<label>.megarc` (e.g. `cuenta1.megarc`). The label is the file name without `.megarc` and is the only way to refer to an account in your messages. Never print, `cat` or copy those files, and never write an email or password in your final text. Juan creates and edits them by hand; never ask for credentials in chat.

Local files in `/root/.openclaw/workspace/skills/mega-keepalive/state/` (git-ignored): `last_ok_<label>` holds the date of the last successful login of that account.

## Steps

### 1. Log in to every account

Run this block exactly as written:

```
cd /root/.openclaw/workspace/skills/mega-keepalive && mkdir -p state
ls /root/.openclaw/credentials/mega/*.megarc >/dev/null 2>&1 || echo "NO-ACCOUNTS"
for f in /root/.openclaw/credentials/mega/*.megarc; do
  [ -f "$f" ] || continue
  n=$(basename "$f" .megarc)
  if out=$(timeout 120 megatools df --config "$f" --no-ask-password --human 2>&1); then
    date '+%Y-%m-%d %H:%M' > "state/last_ok_$n"; echo "$n OK"
  else
    echo "$n FAIL: $(printf '%s\n' "$out" | grep -m1 -i -E 'error|fail' | cut -c1-200)"
  fi
done
```

- `NO-ACCOUNTS` → go to step 4 (failure: "no hay ninguna cuenta configurada en /root/.openclaw/credentials/mega/").
- Every line `<label> OK` → go to step 4 (all OK).
- Any `<label> FAIL: ...` → step 2.

### 2. Retry the failed accounts once

Wait 2 minutes (`sleep 120`), then run this block, replacing `LABELS` with the failed labels separated by spaces (e.g. `cuenta2` or `cuenta1 cuenta2`):

```
cd /root/.openclaw/workspace/skills/mega-keepalive
for n in LABELS; do
  f=/root/.openclaw/credentials/mega/$n.megarc
  if out=$(timeout 120 megatools df --config "$f" --no-ask-password --human 2>&1); then
    date '+%Y-%m-%d %H:%M' > "state/last_ok_$n"; echo "$n OK"
  else
    echo "$n FAIL: $(printf '%s\n' "$out" | grep -m1 -i -E 'error|fail' | cut -c1-200)"
  fi
done
```

Don't retry more than once, and don't try other tools or other ways to log in.

### 3. Last successful login of the failed accounts

For each account that still fails:

```
cat /root/.openclaw/workspace/skills/mega-keepalive/state/last_ok_LABEL 2>/dev/null || echo nunca
```

### 4. Final text

- **All accounts OK:** your whole final text is exactly `NO_REPLY` (nothing else, no explanation). That makes the automation send nothing.
- **Any failure:** a short message in Spanish for Juan, no preamble, like:

  ```
  ⚠️ MEGA: no he podido iniciar sesión en cuenta2 (último login correcto: 2026-12-01 10:00).
  Error: Server returned error ENOENT → email o contraseña incorrectos en cuenta2.megarc.
  Entra a mano en https://mega.nz para que la cuenta no se cierre por inactividad.
  ```

  One line per failed account. Mention the accounts that did work only in a closing "OK: cuenta1". Hints for the error line:
  - `ENOENT` → email or password wrong in `<label>.megarc` (or the account no longer exists).
  - `EMFAREQUIRED`, `-26` or anything about 2FA / multi-factor → the account has two-step verification; megatools can't log in to it. Juan must disable 2FA or ask to set it up with MEGAcmd.
  - `402` / `hashcash` / `blocked` → MEGA is blocking megatools; it needs an update (see https://xff.cz/megatools/).
  - Timeout, DNS, `HTTP POST failed` → network problem; the next automatic run is in two months, so Juan should log in by hand now.
