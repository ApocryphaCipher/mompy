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

*Checked:* the `PUT`, its `If-Match` and the 412 are in the `v0.83.0` source (`src/webserver/memory.cpp`) and the research fork uses them daily.
*Not yet checked:* that the **official release binaries** (macOS, Windows, Linux) behave the same. STORY-008.

## Only in the research fork (mompy must not depend on them)

`webserver_allow_writes` (a gate: with it off the fork refuses writes with 403; **upstream has no such gate**: writes work whenever the server is on),
`POST /capture/screenshot`, `dosbox/pause` and `resume`, signature watching and a DOS file-call log. `momctl` may use a screenshot or pause
if the server has them, and must say it is not available otherwise.

## Speed and size

Emulated memory is 16 MiB. Reading one 0x4C8-byte wizard record is a single small request. `gama` reads the whole 16 MiB for a checkpoint.
