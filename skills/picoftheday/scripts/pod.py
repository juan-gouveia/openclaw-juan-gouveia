#!/usr/bin/env python3
"""Picture of the Day helper.

Subcommands:
  schedule           Pick a random time in today's window and create a one-shot request job.
  request            Mark today as pending and print the request message (stdout -> Telegram).
  status             Print today's state as JSON.
  upload [--force]   Upload Juan's latest Telegram photo to Drive as "picoftheday - NNN - DD-MM-YY".
  list               List stored pictures in the Drive folder (and the ones still queued).
  flush              Upload queued pictures (those that could not be uploaded because Zapier failed).

Listing goes straight to the Google Drive API with a service account (the folder must be shared with it).
If the Zapier upload fails (e.g. the monthly task limit is exceeded) the photo is queued in queue_dir and
uploaded later by `flush`, which also runs before the daily `schedule` and before every new upload.
Only the upload still uses Zapier: the service account has no Drive quota, so it cannot create files.

The bot token is never printed; any output that could contain it is masked.
"""
import argparse
import base64
import json
import random
import re
import sqlite3
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG = json.loads((SKILL_DIR / "config.json").read_text())
STATE_PATH = SKILL_DIR / "state.json"
DB_PATH = "/root/.openclaw/state/openclaw.sqlite"
TZ = ZoneInfo(CONFIG["tz"])
DRIVE_API = "GoogleDriveCLIAPI"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
TOKEN_RE = re.compile(r"bot\d+:[A-Za-z0-9_-]+")


def now():
    return datetime.now(TZ)


def today():
    return now().strftime("%Y-%m-%d")


def mask(text):
    return TOKEN_RE.sub("bot***", text)


def load_state():
    try:
        return json.loads(STATE_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def set_day(day=None, **fields):
    state = load_state()
    day = state.setdefault(day or today(), {})
    day.update(fields)
    save_state(state)
    return day


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


class ZapierError(Exception):
    pass


def zapier(tool, action, tool_name, params):
    args = {"selected_api": DRIVE_API, "action": action, "tool_name": tool_name, "params": params}
    # --no-oauth: fail fast with 401 instead of waiting for a browser login nobody will do.
    res = run([CONFIG["mcporter_bin"], "--config", CONFIG["mcporter_config"], "call",
               f"zapier.{tool}", "--no-oauth", "--args", json.dumps(args)], timeout=180)
    out = res.stdout.strip()
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        err = out + res.stderr
        if "401" in err or "auth required" in err.lower() or "OAuth" in err:
            raise ZapierError("Zapier necesita volver a autorizarse: hay que ejecutar 'mcporter auth zapier' en el servidor.")
        raise ZapierError(f"Error de Zapier: {mask(err)[:500]}")
    return data


def b64url(data):
    if isinstance(data, str):
        data = data.encode()
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def google_token():
    """Access token for the service account (read-only Drive), signed with openssl."""
    sa = json.loads(Path(CONFIG["google_sa_path"]).read_text())
    t = int(now().timestamp())
    claims = {"iss": sa["client_email"], "scope": "https://www.googleapis.com/auth/drive.readonly",
              "aud": GOOGLE_TOKEN_URL, "iat": t, "exp": t + 3600}
    signing_input = b64url(json.dumps({"alg": "RS256", "typ": "JWT"})) + "." + b64url(json.dumps(claims))
    with tempfile.NamedTemporaryFile("w", suffix=".pem") as key:  # created 0600, deleted on close
        key.write(sa["private_key"])
        key.flush()
        res = subprocess.run(["openssl", "dgst", "-sha256", "-sign", key.name],
                             input=signing_input.encode(), capture_output=True)
    if res.returncode != 0:
        sys.exit("No se pudo firmar el token de Google (openssl falló).")
    body = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                   "assertion": signing_input + "." + b64url(res.stdout)}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(GOOGLE_TOKEN_URL, data=body), timeout=30) as r:
            return json.load(r)["access_token"]
    except (urllib.error.URLError, KeyError) as e:
        sys.exit(f"Google no dio token a la cuenta de servicio: {type(e).__name__}")


def google_get(path, params, token):
    req = urllib.request.Request(f"https://www.googleapis.com/drive/v3/{path}?{urllib.parse.urlencode(params)}",
                                 headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            email = json.loads(Path(CONFIG["google_sa_path"]).read_text())["client_email"]
            sys.exit(f"No puedo leer la carpeta de Drive: hay que compartirla con la cuenta de servicio ({email}) como lector.")
        sys.exit(f"Error de Google Drive: HTTP {e.code}")
    except urllib.error.URLError as e:
        sys.exit(f"No se pudo consultar Google Drive: {e.reason}")


def drive_files(name_query=None):
    token = google_token()
    # An unshared folder makes the file query return [] instead of an error, which would reset the
    # numbering and defeat the duplicate guard, so check access to the folder first.
    google_get(f"files/{CONFIG['drive_folder_id']}", {"fields": "id"}, token)
    q = f"'{CONFIG['drive_folder_id']}' in parents and trashed = false and name contains 'picoftheday'"
    if name_query:
        q += f" and name contains '{name_query}'"
    data = google_get("files", {"q": q, "orderBy": "name desc", "pageSize": "100",
                                "fields": "files(id,name,webViewLink)"}, token)
    return [{"name": f["name"], "id": f["id"],
             "link": f.get("webViewLink") or f"https://drive.google.com/file/d/{f['id']}/view"}
            for f in data.get("files", [])]


# --- subcommands -------------------------------------------------------------

def cmd_schedule(_):
    if load_queue():
        try:
            up, rem = flush_queue(drive_files())
            print(f"Cola de fotos: {up} subidas, {rem} pendientes.")
        except SystemExit as e:
            print(f"Cola de fotos: no se pudo procesar ({e}).")
    state = load_state()
    # Past days that never got a photo become "missed".
    for day, info in state.items():
        if day < today() and info.get("status") in ("scheduled", "pending"):
            info["status"] = "missed"
    save_state(state)

    if state.get(today(), {}).get("status") in ("scheduled", "pending", "done", "queued"):
        print(f"Hoy ya está {state[today()]['status']}; no se programa nada.")
        return

    n = now()
    start_h, start_m = map(int, CONFIG["window"][0].split(":"))
    end_h, end_m = map(int, CONFIG["window"][1].split(":"))
    start = n.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end = n.replace(hour=end_h, minute=end_m, second=0, microsecond=0) - timedelta(minutes=1)
    start = max(start, (n + timedelta(minutes=2)).replace(second=0, microsecond=0))
    if start > end:
        print("La ventana de hoy ya pasó; no se programa nada.")
        return
    minutes = int((end - start).total_seconds() // 60)
    at = start + timedelta(minutes=random.randint(0, minutes))
    at_str = at.strftime("%Y-%m-%dT%H:%M")

    script = Path(__file__).resolve()
    res = run(["openclaw", "automations", "add",
               "--name", f"picoftheday-request-{today()}",
               "--at", at_str, "--tz", CONFIG["tz"], "--delete-after-run",
               "--command-argv", json.dumps(["python3", str(script), "request"]),
               "--announce", "--channel", "telegram", "--to", CONFIG["telegram_to"]])
    if res.returncode != 0:
        sys.exit(f"No se pudo crear el job: {mask(res.stderr or res.stdout)[:500]}")
    set_day(status="scheduled", at=at.strftime("%H:%M"))
    print(f"Petición programada para {at_str} ({CONFIG['tz']}).")


def cmd_request(_):
    set_day(status="pending", requested_at=now().isoformat(timespec="seconds"))
    print(CONFIG["request_message"])


def cmd_status(_):
    print(json.dumps({"date": today(), **load_state().get(today(), {"status": "none"}),
                      "queued": len(load_queue())}, ensure_ascii=False))


def latest_photo():
    """Newest photo (or image document) Juan sent to the bot, from OpenClaw's Telegram message cache."""
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    rows = con.execute(
        "select value_json from plugin_state_entries where plugin_id='telegram' "
        "and namespace='telegram.message-cache' and entry_key like ? order by created_at desc limit 20",
        (f"%:{CONFIG['telegram_to']}:%",)).fetchall()
    for (raw,) in rows:
        msg = json.loads(raw).get("sourceMessage", {})
        if str(msg.get("from", {}).get("id")) != CONFIG["telegram_to"]:
            continue
        if msg.get("photo"):
            best = max(msg["photo"], key=lambda p: p.get("file_size", 0))
            return best["file_id"], "jpg", msg
        doc = msg.get("document") or {}
        if doc.get("mime_type", "").startswith("image/"):
            ext = doc.get("file_name", "img.jpg").rsplit(".", 1)[-1].lower()
            return doc["file_id"], ext, msg
    return None, None, None


def get_token():
    res = run(["openclaw", "secrets", "store", "get", CONFIG["token_env_name"], "--plain"])
    token = res.stdout.strip()
    if not re.fullmatch(r"\d+:[A-Za-z0-9_-]{30,}", token):
        sys.exit(f"No se pudo leer {CONFIG['token_env_name']} del secret store.")
    return token


def telegram_file_url(file_id):
    token = get_token()
    with urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/getFile?file_id={urllib.parse.quote(file_id)}") as r:
        file_path = json.load(r)["result"]["file_path"]
    return f"https://api.telegram.org/file/bot{token}/{file_path}"


def drive_upload(file_id, ext, name):
    """Upload a Telegram photo to the Drive folder through Zapier. Raises ZapierError on any failure."""
    data = zapier("execute_zapier_write_action", "file", "google_drive_upload_file",
                  {"file": telegram_file_url(file_id), "new_name": name, "new_extension": ext})
    result = (data.get("results") or [{}])[0]
    if not result.get("id"):
        raise ZapierError(f"La subida no devolvió un archivo: {mask(json.dumps(data))[:500]}")
    link = result.get("alternateLink") or f"https://drive.google.com/file/d/{result['id']}/view"
    return result, link


def next_name(files, date_str):
    # Next number = highest existing number + 1, so gaps or deletions never cause a repeat.
    numbers = [int(m.group(1)) for f in files if (m := re.match(r"picoftheday - (\d+) - ", f["name"]))]
    return CONFIG["name_pattern"].format(n=max(numbers, default=0) + 1, date=date_str)


# --- queue: photos waiting for Zapier ----------------------------------------------

QUEUE_DIR = Path(CONFIG["queue_dir"])


def load_queue():
    try:
        return json.loads((QUEUE_DIR / "queue.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_queue(queue):
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    (QUEUE_DIR / "queue.json").write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n")


def queue_add(file_id, ext, date_str, reason):
    """Queue a photo and keep a local copy next to the queue (the Telegram file_id is what flush uses)."""
    entry = {"file_id": file_id, "ext": ext, "date": date_str, "day": today(),
             "queued_at": now().isoformat(timespec="seconds"), "reason": mask(reason)[:200]}
    try:
        photos = QUEUE_DIR / "photos"
        photos.mkdir(parents=True, exist_ok=True)
        local = photos / f"{today()}-{file_id[-8:]}.{ext}"
        urllib.request.urlretrieve(telegram_file_url(file_id), local)
        entry["local_copy"] = str(local)
    except Exception:
        pass  # best effort: the file_id alone is enough to upload later
    save_queue(load_queue() + [entry])
    set_day(status="queued", queued_at=entry["queued_at"])
    return entry


def flush_queue(files):
    """Upload queued photos in order; stop at the first failure. Returns (uploaded, remaining)."""
    queue = load_queue()
    uploaded = 0
    while queue:
        entry = queue[0]
        name = next_name(files, entry["date"])
        try:
            result, link = drive_upload(entry["file_id"], entry["ext"], name)
        except (ZapierError, urllib.error.URLError) as e:
            entry["last_error"] = mask(str(e))[:200]
            entry["last_try"] = now().isoformat(timespec="seconds")
            save_queue(queue)
            break
        files.append({"name": f"{name}.{entry['ext']}", "id": result["id"], "link": link})
        set_day(entry["day"], status="done", drive_file_id=result["id"], name=f"{name}.{entry['ext']}",
                link=link, uploaded_at=now().isoformat(timespec="seconds"), from_queue=True)
        queue.pop(0)
        save_queue(queue)
        uploaded += 1
    return uploaded, len(queue)


def cmd_flush(_):
    if not load_queue():
        print(json.dumps({"result": "empty"}))
        return
    uploaded, remaining = flush_queue(drive_files())
    print(json.dumps({"result": "flushed", "uploaded": uploaded, "remaining": remaining}))


def cmd_upload(args):
    file_id, ext, msg = latest_photo()
    if not file_id:
        sys.exit("No encuentro ninguna foto reciente de Juan en Telegram.")
    sent = datetime.fromtimestamp(msg["date"], TZ).strftime("%Y-%m-%d")
    if sent != today() and not args.force:
        sys.exit(f"La última foto es del {sent}, no de hoy. Usa --force si aun así es la de hoy.")

    date_str = now().strftime(CONFIG["date_format"])
    files = drive_files()
    queued_today = [q for q in load_queue() if q["date"] == date_str]
    existing = [f for f in files if f" - {date_str}." in f["name"]] + \
               [{"name": f"(en cola) {date_str}.{q['ext']}", "queued": True} for q in queued_today]
    if existing and not args.force:
        print(json.dumps({"result": "exists", "files": existing}, ensure_ascii=False))
        sys.exit(3)

    # Older queued photos go first so the numbering stays chronological.
    if load_queue():
        flush_queue(files)
    if load_queue():
        queue_add(file_id, ext, date_str, "cola con fotos pendientes")
        print(json.dumps({"result": "queued", "pending": len(load_queue())}, ensure_ascii=False))
        return

    name = next_name(files, date_str)
    try:
        result, link = drive_upload(file_id, ext, name)
    except (ZapierError, urllib.error.URLError) as e:
        queue_add(file_id, ext, date_str, str(e))
        print(json.dumps({"result": "queued", "pending": len(load_queue()), "reason": mask(str(e))[:200]},
                         ensure_ascii=False))
        return
    set_day(status="done", drive_file_id=result["id"], name=f"{name}.{ext}", link=link,
            uploaded_at=now().isoformat(timespec="seconds"))
    print(json.dumps({"result": "uploaded", "name": f"{name}.{ext}", "size": result.get("fileSize"),
                      "link": link}, ensure_ascii=False))


def cmd_list(_):
    items = drive_files() + [{"name": f"(en cola) {q['date']}.{q['ext']}", "link": None, "queued": True}
                             for q in load_queue()]
    print(json.dumps(items, ensure_ascii=False, indent=1))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("schedule", "request", "status", "list", "flush"):
        sub.add_parser(name)
    up = sub.add_parser("upload")
    up.add_argument("--force", action="store_true")
    args = p.parse_args()
    {"schedule": cmd_schedule, "request": cmd_request, "status": cmd_status,
     "upload": cmd_upload, "list": cmd_list, "flush": cmd_flush}[args.cmd](args)


if __name__ == "__main__":
    main()
