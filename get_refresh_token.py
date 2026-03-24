"""
Run once to get a Google Ads refresh token.

Usage:
    python get_refresh_token.py

The script reads GOOGLE_ADS_CLIENT_ID and GOOGLE_ADS_CLIENT_SECRET from .env
(or prompts you if they're missing), opens a browser for Google consent,
catches the redirect on localhost:8080, then prints the refresh token.

In Google Cloud Console → OAuth client → Authorized redirect URIs, add:
    http://localhost:8080/
"""
import os
import sys
import json
import webbrowser
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


def _load_env() -> None:
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env()

SCOPE = "https://www.googleapis.com/auth/adwords"
AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
REDIRECT_URI = "http://localhost:8080/"


def _prompt(name: str, env_key: str) -> str:
    value = os.environ.get(env_key, "").strip()
    if value:
        masked = value[:6] + "…" + value[-4:] if len(value) > 12 else "***"
        print(f"  {name}: {masked}  (з .env)")
        return value
    return input(f"  {name}: ").strip()


def _exchange_code(code: str, client_id: str, client_secret: str) -> dict:
    data = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(TOKEN_URI, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        sys.exit(f"❌  Помилка від Google: {body.get('error_description', body)}")


def _wait_for_code() -> str:
    """Start a one-shot local server and wait for Google's redirect."""
    received: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # suppress request logs

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)

            if "code" in params:
                received["code"] = params["code"][0]
                body = "<h2>OK! ✅ Можна закрити цю вкладку.</h2>".encode()
            elif "error" in params:
                received["error"] = params["error"][0]
                body = "<h2>Помилка. Перевір термінал.</h2>".encode()
            else:
                body = "<h2>Очікую...</h2>".encode()

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

    server = HTTPServer(("localhost", 8080), Handler)
    server.handle_request()  # handle exactly one request, then stop
    server.server_close()

    if "error" in received:
        sys.exit(f"❌  Google повернув помилку: {received['error']}")
    if "code" not in received:
        sys.exit("❌  Код авторизації не отримано.")

    return received["code"]


def main() -> None:
    print("=" * 60)
    print("  Google Ads OAuth — отримання refresh token")
    print("=" * 60)
    print()
    print("Важливо: у Google Cloud Console → OAuth client")
    print("має бути Authorized redirect URI:")
    print(f"  {REDIRECT_URI}")
    print()
    print("Введіть OAuth credentials:")
    client_id = _prompt("Client ID", "GOOGLE_ADS_CLIENT_ID")
    client_secret = _prompt("Client Secret", "GOOGLE_ADS_CLIENT_SECRET")

    if not client_id or not client_secret:
        sys.exit("❌  Client ID та Client Secret обов'язкові.")

    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = AUTH_URI + "?" + urllib.parse.urlencode(params)

    print()
    print("─" * 60)
    print("Відкриваю браузер для підтвердження доступу…")
    print(f"URL: {auth_url}")
    print()
    webbrowser.open(auth_url)

    print("⏳ Очікую відповідь від Google на localhost:8080…")
    code = _wait_for_code()

    print("⏳ Обмінюю код на токени…")
    tokens = _exchange_code(code, client_id, client_secret)

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        sys.exit(
            "❌  refresh_token не повернуто. "
            "Переконайся що у запиті є prompt=consent і цей акаунт "
            "не був авторизований раніше (або відклич доступ у myaccount.google.com/permissions)."
        )

    print()
    print("=" * 60)
    print("✅  Успішно! Додай у .env:")
    print()
    print(f"GOOGLE_ADS_REFRESH_TOKEN={refresh_token}")
    print("=" * 60)


if __name__ == "__main__":
    main()
