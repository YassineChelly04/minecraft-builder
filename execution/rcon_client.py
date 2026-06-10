"""
Minimal pure-stdlib Source RCON client (socket + struct). Optional execution path
for servers that expose RCON. Guarded: callers must supply a password (the app
refuses rcon mode unless RCON_PASSWORD is set).
"""
from __future__ import annotations

import socket
import struct
import time

_TYPE_AUTH = 3
_TYPE_COMMAND = 2
_TYPE_RESPONSE = 0


class RconError(RuntimeError):
    pass


class RconClient:
    def __init__(self, host: str, port: int, password: str, timeout: float = 5.0):
        self.host, self.port, self.password, self.timeout = host, port, password, timeout
        self._sock: socket.socket | None = None
        self._id = 0

    # ── connection ───────────────────────────────────────────────────────────
    def connect(self) -> "RconClient":
        self._sock = socket.create_connection((self.host, self.port), self.timeout)
        self._sock.settimeout(self.timeout)
        if self._send(_TYPE_AUTH, self.password) == -1:
            raise RconError("RCON authentication failed (bad password)")
        return self

    def close(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, *exc):
        self.close()

    # ── protocol ─────────────────────────────────────────────────────────────
    def _send(self, ptype: int, body: str) -> int:
        if not self._sock:
            raise RconError("not connected")
        self._id += 1
        payload = struct.pack("<ii", self._id, ptype) + body.encode("utf-8") + b"\x00\x00"
        self._sock.sendall(struct.pack("<i", len(payload)) + payload)
        resp_id, _, _ = self._recv()
        return resp_id

    def _recv(self) -> tuple[int, int, str]:
        length = struct.unpack("<i", self._read(4))[0]
        data = self._read(length)
        resp_id, ptype = struct.unpack("<ii", data[:8])
        body = data[8:-2].decode("utf-8", errors="replace")
        return resp_id, ptype, body

    def _read(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise RconError("connection closed")
            buf += chunk
        return buf

    # ── commands ─────────────────────────────────────────────────────────────
    def run(self, cmd: str) -> str:
        if not self._sock:
            raise RconError("not connected")
        self._id += 1
        body = cmd.lstrip("/")
        payload = struct.pack("<ii", self._id, _TYPE_COMMAND) + body.encode("utf-8") + b"\x00\x00"
        self._sock.sendall(struct.pack("<i", len(payload)) + payload)
        _, _, out = self._recv()
        return out

    def run_many(self, cmds: list[str], per_second: int = 200) -> int:
        delay = 1.0 / max(1, per_second)
        n = 0
        for c in cmds:
            self.run(c)
            n += 1
            time.sleep(delay)
        return n
