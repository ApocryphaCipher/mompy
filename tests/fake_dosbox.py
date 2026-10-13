"""A fake DOSBox web API for the tests: a 16 MiB memory image behind the endpoints mompy uses."""

from __future__ import annotations

import base64
import json
import re
import struct
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from mompy import layout

MEMORY_SIZE = 16 * 1024 * 1024


def game_memory(base: int = layout.REFERENCE_WIZARD_BASE,
                names=("Jafar", "Freya", "Sss'ra", "Sharee", "Tauron"),
                cities: int = 3, units: int = 4, nodes: int = 2) -> bytearray:
    """A memory image with a plausible game in it, its wizard table at ``base``."""
    mem = bytearray(MEMORY_SIZE)
    shift = base - layout.REFERENCE_WIZARD_BASE
    for i, name in enumerate(names):
        at = base + i * layout.WIZARD_STRIDE + layout.WIZARD_NAME_AT
        mem[at:at + layout.WIZARD_NAME_LEN] = name.encode().ljust(layout.WIZARD_NAME_LEN, b"\0")
    for i in range(cities):
        at = layout.CITIES.reference + shift + i * layout.CITIES.stride
        mem[at:at + 14] = f"City{i}".encode().ljust(14, b"\0")
        mem[at + 14:at + 19] = bytes([1, 10 + i, 20, 0, i % 5])        # race, x, y, plane, owner
    for i in range(units):
        at = layout.UNITS.reference + shift + i * layout.UNITS.stride
        mem[at:at + 6] = bytes([5 + i, 7, 0, i % 5, 2, 40])            # x, y, plane, owner, moves, type
    struct.pack_into("<H", mem, layout.UNIT_COUNT_REFERENCE + shift, units)
    for i in range(nodes):
        at = layout.NODES.reference + shift + i * layout.NODES.stride
        mem[at:at + 4] = bytes([30 + i, 9, 0, 0xFF])                   # x, y, plane, owner -1
    return mem


class FakeDosbox:
    """``with FakeDosbox(memory, version="0.84.0-alpha (5b1f1d)") as fake: fake.url``."""

    def __init__(self, memory: bytearray, version: str = "0.84.0-alpha (5b1f1d)",
                 allow_writes: bool = True, race_on_write: bool = False,
                 fail_write_number: int = 0):
        self.memory = memory
        self.version = version
        self.allow_writes = allow_writes
        self.race_on_write = race_on_write      # change the byte just before a write is checked
        self.fail_write_number = fail_write_number   # make the nth PUT answer 500 (1 is the first)
        self.requests = []                      # (method, path) of every request, to count what a command reads
        self.puts = 0
        self.writes = []                        # (address, data) of accepted writes
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, code, body, ctype="application/json"):
                data = body if isinstance(body, bytes) else json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                fake.requests.append(("GET", self.path))
                if self.path == "/api/v1/dosbox/info":
                    return self._send(200, {"version": fake.version, "configHome": "/x", "configWebserver": "/y"})
                m = re.fullmatch(r"/api/v1/memory/(\d+)/(\d+)", self.path)
                if m:
                    a, n = int(m[1]), int(m[2])
                    return self._send(200, bytes(fake.memory[a:a + n]), "application/octet-stream")
                self._send(404, {"error": "not found"})

            def do_PUT(self):
                fake.requests.append(("PUT", self.path))
                m = re.fullmatch(r"/api/v1/memory/(\d+)", self.path)
                if not m:
                    return self._send(404, {"error": "not found"})
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                if not fake.allow_writes:
                    return self._send(403, {"error": "State-changing requests are disabled; "
                                                     "set 'webserver_allow_writes = true' to enable them"})
                fake.puts += 1
                if fake.fail_write_number and fake.puts == fake.fail_write_number:
                    return self._send(500, {"error": "boom"})
                a = int(m[1])
                expected = self.headers.get("If-Match")
                if fake.race_on_write:
                    fake.memory[a] = (fake.memory[a] + 1) % 256
                if expected is not None:
                    want = base64.b64decode(expected.strip('"'))
                    have = bytes(fake.memory[a:a + len(want)])
                    if want != have:
                        return self._send(412, {"memory": {"addr": a, "data": base64.b64encode(have).decode()}})
                fake.memory[a:a + len(body)] = body
                fake.writes.append((a, body))
                self._send(200, {"memory": {"addr": a}})

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()


def put_field(mem: bytearray, base: int, block: str, number: int, name: str, value) -> None:
    """Set one field of record ``number`` in a game memory image (with the same encoder ``poke`` will use)."""
    from mompy import fields as F

    blk = F.blocks()[block]
    field = F.find(block, name)
    at = base + (number - blk.first_number) * blk.stride + field.offset
    mem[at:at + field.size] = field.encode(value)


import os
import tempfile
import unittest
from unittest import mock


class HomeTestCase(unittest.TestCase):
    """A test case whose ``MOMPY_HOME`` is a throwaway folder: the cache and the undo log never touch the real ``~/.mompy``."""

    def setUp(self):
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = tmp.name
        env = mock.patch.dict(os.environ, {"MOMPY_HOME": tmp.name})
        env.start()
        self.addCleanup(env.stop)
