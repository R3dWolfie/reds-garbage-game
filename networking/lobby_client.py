# networking/lobby_client.py
"""
Internet lobby client — registers hosted games and queries the lobby server.
Works alongside the existing LAN broadcast system.
"""

import threading
import time
import json
from urllib.request import urlopen, Request
from urllib.error import URLError

try:
    from updater.version import LOBBY_URL, VERSION
except ImportError:
    LOBBY_URL = "https://updates.r3dwolfie.com/api/lobby"
    VERSION = "0.0.0"


class LobbyRegister:
    """Runs in background — periodically heartbeats to the lobby server while hosting."""

    def __init__(self, lobby_name, port, max_players, has_password=False):
        self.lobby_name = lobby_name
        self.port = port
        self.max_players = max_players
        self.has_password = has_password
        self.player_count = 1
        self.running = False
        self._thread = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        # Send DELETE to unregister
        try:
            data = json.dumps({"port": self.port}).encode("utf-8")
            req = Request(LOBBY_URL, data=data, method="DELETE",
                          headers={"Content-Type": "application/json",
                                   "User-Agent": f"RGG/{VERSION}"})
            urlopen(req, timeout=5)
        except Exception as e:
            print(f"[Lobby] Unregister failed: {e}")

    def update_player_count(self, count):
        self.player_count = count

    def _loop(self):
        while self.running:
            try:
                data = json.dumps({
                    "name": self.lobby_name,
                    "port": self.port,
                    "players": self.player_count,
                    "max_players": self.max_players,
                    "has_password": self.has_password,
                    "version": VERSION,
                }).encode("utf-8")
                req = Request(LOBBY_URL, data=data, method="POST",
                              headers={"Content-Type": "application/json",
                                       "User-Agent": f"RGG/{VERSION}"})
                resp = urlopen(req, timeout=5)
                result = json.loads(resp.read().decode("utf-8"))
                if result.get("status") == "ok":
                    pass  # Registered successfully
            except Exception as e:
                print(f"[Lobby] Heartbeat failed: {e}")

            # Heartbeat every 10 seconds
            for _ in range(100):
                if not self.running:
                    return
                time.sleep(0.1)


def fetch_internet_servers():
    """
    Query the lobby server for all active internet games.
    Returns list of server dicts, or empty list on failure.
    """
    try:
        req = Request(LOBBY_URL, headers={"User-Agent": f"RGG/{VERSION}"})
        resp = urlopen(req, timeout=5)
        servers = json.loads(resp.read().decode("utf-8"))
        if isinstance(servers, list):
            return servers
        return []
    except Exception as e:
        print(f"[Lobby] Fetch failed: {e}")
        return []