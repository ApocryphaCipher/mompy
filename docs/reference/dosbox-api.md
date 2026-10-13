# DOSBox Staging's web API, as mompy uses it

**Sources:** DOSBox Staging's own source (`src/webserver/`, tag `v0.83.0` and `main` of 2026-10-13, read 2026-10-13), and Kevin's research fork
(`ApocryphaCipher/dosbox-staging`, branch `webserver-write-guard`) and Mirror's `docs/reference/live-ram-map.md`, which record what was
tried against a running game.

## Turn it on

`webserver_enabled = true` in DOSBox's config (or `--set webserver_enabled=true`). It listens on `127.0.0.1:8086` by default
(`webserver_port`, `webserver_bind_address`), answers only requests whose `Host` header names that address (a guard against DNS rebinding), and is **off by
default**. `v0.83.0` (2026-08-26) already has it; it is compiled in without a build option.

## What mompy uses

| Request | Does |
| --- | --- |
| `GET /api/v1/dosbox/info` | version and config paths: `doctor` uses it to see the server is there |
| `GET /api/v1/memory/:offset/:len` | `len` bytes from a **linear** address (decimal, or hex with `0x`) |
| `PUT /api/v1/memory/:offset` | writes the body there. `Content-Type: application/octet-stream` (raw bytes) or JSON. **With `If-Match: "<base64 of the bytes you expect>"` it is a compare-and-swap:** on a mismatch the answer is **412** and nothing changes |

*Checked in the source:* the `PUT`, its `If-Match` and the 412 are in the `v0.83.0` source (`src/webserver/memory.cpp`), and the research fork uses them daily.

## Checked on the released binaries (STORY-008)

| Platform | Release file | Result |
| --- | --- | --- |
| **macOS** (Apple silicon, 2026-10-13) | `dosbox-staging-macOS-v0.83.0.dmg`, 42 MB, sha256 `d8a771adfb8010fa6b5f7fb5351abfba659273ad01c89f03675a92bdbdae8167` (the digest GitHub lists for the release); app signed with the project's Developer ID (team `944SS92GAH`); reports **`0.83.0 (7b400)`** | **Works**, below |
| Windows (`...windows-x64-v0.83.0.zip` and `-setup.exe`) | | *not tried: needs a tester* |
| Linux (`...linux-x86_64-v0.83.0.tar.xz`) | | *not tried: needs a tester* |

What was done on macOS: the app was copied out of the mounted image (not installed) and started from a terminal, with a throwaway config and no display
(`SDL_VIDEODRIVER=dummy`), `--noprimaryconf --nolocalconf --set webserver_enabled=true --set webserver_port=8186`. The copied app carried `com.apple.quarantine`; started from Terminal it did not
prompt (a double-click through Finder was *not* tried). Against a scratch address in extended memory (`0x300000`, nothing there):

- `GET /api/v1/dosbox/info` answers (`version`, `configHome`, `configWebserver`).
- `GET /api/v1/memory/:addr/4` reads four bytes.
- `PUT` with `If-Match: "AAAAAA=="` (the bytes expected, base64) and the body `01 02 03 04` answers **200** and the bytes are written; read back, they are `01 02 03 04`.
- `PUT` with a **wrong** `If-Match` answers **412 and changes nothing**; the answer's body carries the *current* bytes (`"data": "AQIDBA=="`), which `momctl` can show in its error.
- `PUT` with the right expectation again writes (`aa bb cc dd`).
- A request with another `Host` header gets **403** (the rebinding guard).
- `GET /cpu/state` and `GET /dos/internals` answer 200. **`POST /capture/screenshot`, `/dosbox/pause`, `/dosbox/resume` and `/signatures/reload` are 404**: they are the research fork's, as expected.
- No write gate: with `webserver_enabled` on, the write was allowed with no other setting.

*Not yet checked:* the same on the **real game** in the released build (STORY-008 step 4), and Windows and Linux.

## Only in the research fork (mompy must not depend on them)

`webserver_allow_writes` (a gate: with it off the fork refuses writes with 403; **upstream has no such gate**: writes work whenever the server is on),
`POST /capture/screenshot`, `dosbox/pause` and `resume`, signature watching and a DOS file-call log. `momctl` may use a screenshot or pause
if the server has them, and must say it is not available otherwise.

## Speed and size

Emulated memory is 16 MiB. Reading one 0x4C8-byte wizard record is a single small request. `gama` reads the whole 16 MiB for a checkpoint.
