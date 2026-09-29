#!/usr/bin/env python3
"""Picture of the Day helper.

Subcommands:
  schedule           Pick a random time in today's window and create a one-shot request job.
  request            Mark today as pending and print the request message (stdout -> Telegram).
  status             Print today's state as JSON.
  upload [--force]   Upload Juan's latest Telegram photo to Drive as "picoftheday - NNN - DD-MM-YY".
  list               List stored pictures in the Drive folder.

The bot token is never printed; any output that could contain it is masked.
"""
import argparse
import json
import random
import re
import sqlite3
import subprocess
import sys
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


def set_day(**fields):
    state = load_state()
    day = state.setdefault(today(), {})
    day.update(fields)
    save_state(state)
    return day


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


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
            sys.exit("Zapier necesita volver a autorizarse: hay que ejecutar 'mcporter auth zapier' en el servidor.")
        sys.exit(f"Error de Zapier: {mask(err)[:500]}")
    return data


def drive_files(name_query=None):
    q = f"'{CONFIG['drive_folder_id']}' in parents and trashed = false and name contains 'picoftheday'"
    if name_query:
        q += f" and name contains '{name_query}'"
    data = zapier("execute_zapier_write_action", "ae_42227_google_drive_retrieve_files_from_google_d",
                  "google_drive_retrieve_files_from_google_drive",
                  {"customQuery": q, "orderBy": "name desc", "pageSize": "100"})
    text = json.dumps(data)
    files = []
    for m in re.finditer(r'\{[^{}]*"name":\s*"(picoftheday[^"]*)"[^{}]*\}', text):
        obj = json.loads(m.group(0))
        files.append({"name": obj["name"], "id": obj.get("id"),
                      "link": f"https://drive.google.com/file/d/{obj.get('id')}/view"})
    return files


# --- subcommands -------------------------------------------------------------

def cmd_schedule(_):
    state = load_state()
    # Past days that never got a photo become "missed".
    for day, info in state.items():
        if day < today() and info.get("status") in ("scheduled", "pending"):
            info["status"] = "missed"
    save_state(state)

    if state.get(today(), {}).get("status") in ("scheduled", "pending", "done"):
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
    print(json.dumps({"date": today(), **load_state().get(today(), {"status": "none"})}, ensure_ascii=False))


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


def cmd_upload(args):
    file_id, ext, msg = latest_photo()
    if not file_id:
        sys.exit("No encuentro ninguna foto reciente de Juan en Telegram.")
    sent = datetime.fromtimestamp(msg["date"], TZ).strftime("%Y-%m-%d")
    if sent != today() and not args.force:
        sys.exit(f"La última foto es del {sent}, no de hoy. Usa --force si aun así es la de hoy.")

    date_str = now().strftime(CONFIG["date_format"])
    files = drive_files()
    existing = [f for f in files if f" - {date_str}." in f["name"]]
    if existing and not args.force:
        print(json.dumps({"result": "exists", "files": existing}, ensure_ascii=False))
        sys.exit(3)
    # Next number = highest existing number + 1, so gaps or deletions never cause a repeat.
    numbers = [int(m.group(1)) for f in files if (m := re.match(r"picoftheday - (\d+) - ", f["name"]))]
    name = CONFIG["name_pattern"].format(n=max(numbers, default=0) + 1, date=date_str)

    token = get_token()
    with urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/getFile?file_id={urllib.parse.quote(file_id)}") as r:
        file_path = json.load(r)["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{token}/{file_path}"

    data = zapier("execute_zapier_write_action", "file", "google_drive_upload_file",
                  {"file": url, "new_name": name, "new_extension": ext})
    result = (data.get("results") or [{}])[0]
    if not result.get("id"):
        sys.exit(f"La subida no devolvió un archivo: {mask(json.dumps(data))[:500]}")
    link = result.get("alternateLink") or f"https://drive.google.com/file/d/{result['id']}/view"
    set_day(status="done", drive_file_id=result["id"], name=f"{name}.{ext}", link=link,
            uploaded_at=now().isoformat(timespec="seconds"))
    print(json.dumps({"result": "uploaded", "name": f"{name}.{ext}", "size": result.get("fileSize"),
                      "link": link}, ensure_ascii=False))


def cmd_list(_):
    print(json.dumps(drive_files(), ensure_ascii=False, indent=1))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("schedule", "request", "status", "list"):
        sub.add_parser(name)
    up = sub.add_parser("upload")
    up.add_argument("--force", action="store_true")
    args = p.parse_args()
    {"schedule": cmd_schedule, "request": cmd_request, "status": cmd_status,
     "upload": cmd_upload, "list": cmd_list}[args.cmd](args)


if __name__ == "__main__":
    main()
