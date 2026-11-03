"""Native window entry point — this is what the packaged .app runs. Closing the window quits the app."""
import os
import socket
import sys
import threading
import time
import urllib.request

import webview

import backups
import db
from app import VERSION, app


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> None:
    if getattr(sys, "frozen", False):  # a packaged .app has no terminal: keep a log next to the data
        db.DATA_DIR.mkdir(parents=True, exist_ok=True)
        sys.stdout = sys.stderr = open(db.DATA_DIR / "app.log", "a", buffering=1, encoding="utf-8")
    backups.open_database(VERSION)  # backs up budget.db first when this is a new version
    port = free_port()
    app.config["DESKTOP"] = True
    threading.Thread(target=lambda: app.run(host="127.0.0.1", port=port, threaded=True, use_reloader=False),
                     daemon=True).start()
    url = f"http://127.0.0.1:{port}/"
    for _ in range(100):
        try:
            urllib.request.urlopen(url, timeout=0.2)
            break
        except OSError:
            time.sleep(0.05)

    webview.settings["ALLOW_DOWNLOADS"] = True              # "Xuất CSV" saves to Downloads
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True  # Google account pages open in Safari/Chrome
    # Smoke tests launch the real bundle; a hidden window keeps it off the screen and safe from a stray click.
    hidden = os.environ.get("THUCHI_HIDDEN_WINDOW") == "1"
    webview.create_window("Thu Chi Gia Đình", url, width=1200, height=820, min_size=(420, 640),
                          background_color="#f4f5fb", hidden=hidden)
    webview.start()


if __name__ == "__main__":
    main()
