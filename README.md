<p align="center">
  <img src="ollamaskope.jpg" alt="Ollamaskope V.1.0.1 " width="100%">
</p>

German: [README.ger.md](README.ger.md)

# Ollamaskope – model list of an Ollama endpoint as a web tool

Shows the models of a remote (or local) Ollama endpoint, turns any model into a
portable Modelfile, builds a new model from it, deletes models and rolls one out
onto another endpoint. Pure Python 3 (standard library), no Flask, no
Node dependencies.

The tool does not run inference and therefore does not belong on an inference
host. It only talks to the Ollama API over HTTP.

## Installation

```bash
cd ~/ollamaskope
./install.sh                # check and set up
./install.sh --start        # set up and start right away
./install.sh --check        # check only, change nothing
```

The installer checks `python3` (3.8 or newer) and `curl`, sets the executable
bits, creates `config.json` from `config.example.json` – an existing
`config.json` is left untouched – and writes the shortcut
`~/.local/bin/ollamaskope`, which forwards `start|stop|restart|status`
(`--ohne-befehl` skips it).

**No venv.** The tool uses only the Python standard library (`http.server`,
`urllib`, `json`, `threading`); a venv would be an empty shell with one more
thing to break. If a `requirements.txt` ever appears, `install.sh` creates
`.venv` and installs it; `ollamaskope.sh` then prefers `.venv/bin/python`
(`OLLAMASKOPE_OHNE_VENV=1` turns that off).

## Installing over the LAN with curl

If the service runs on a host in your LAN, one line on another machine is
enough – package and installer come from that host:

```bash
curl -fsSL http://127.0.0.1:8090/get.sh | sh
```

The script asks whether the service should listen on `127.0.0.1` only or on
`0.0.0.0` in the LAN, unpacks to `~/ollamaskope`, runs `install.sh` and finally
asks whether to start it. Without a terminal (from a script, for example)
`config.json` stays unchanged and nothing is started:

```bash
curl -fsSL http://127.0.0.1:8090/get.sh | sh -s -- --bind 0.0.0.0 --start
```

Options: `--bind 127.0.0.1|0.0.0.0`, `--quelle URL` (another package),
`--ziel PATH`, `--start`, `--ohne-start`, `--hilfe`. A second run is an update:
program and UI are replaced, `config.json` and `ollamaskope.conf` survive.

The package is produced by `./paket-bauen.sh` and lands in
`static/ollamaskope.tar.gz` (without `config.json`, PID/log files, `.venv`).
Rebuild it after changing the program:

```bash
./paket-bauen.sh            # then: curl …/get.sh | sh
```

## Running

```bash
cd ~/ollamaskope
./ollamaskope.sh start      # starts in the background, checks /api/gesundheit
./ollamaskope.sh status
./ollamaskope.sh stop
```

Then open **http://127.0.0.1:8090/**

Without the start script (blocks the terminal):

```bash
python3 ollamaskope.py --port 8090
```

## Usage

| Step | What happens |
|---|---|
| Pick an endpoint | list comes from `/api/tags`, loaded models are marked |
| **Modelfile** | `/api/show` becomes an editable Modelfile; “Als Datei” saves it as `Modelfile` |
| Enter a name, **Modell erzeugen** | `/api/create` streams its progress into the log |
| **Delete** | only once a model is open: button in the Modelfile editor and in the dependency view; a confirmation names the model, “Ja, löschen” sends `/api/delete` |
| **Roll out** | open a model, “⇄ Ausrollen”: pick target endpoint and name. The recipe is transferred (FROM, parameters, template, system), not the weights – the base must be present on the target or is pulled there first |
| **Load / unload** | per row: load a model into memory (`keep_alive` 30 min) or drop it (`keep_alive` 0) – the counterpart of `ollama run` |
| **Click a model** | overview: what it is built on, what is built on it, siblings – with “Dieses Modell löschen” |
| **Click a column head** | sorts by model, size, family, parameter count, quantisation or date; a second click reverses, a third restores server order |
| **＋ Endpunkt** | add an endpoint by name and URL (URL is checked first) or remove one; both end up in `config.json` |

Every load and unload attempt is also appended to `laden.log` next to the
program – one tab-separated line per attempt:

```text
2026-11-17T02:13:54	laden	fake	http://127.0.0.1:11434	klein:latest	1.84s	ok done_reason=load
```

In order: time, action (`laden`/`entladen`), endpoint name, endpoint URL, model,
duration, result. Failures appear as `fehler: …` – they are the lines that later
answer why a 200 came back while nothing was actually in memory. The access
lines in `ollamaskope.log` do not tell you that.

The action buttons of each row sit in the **first column, on the left**, ahead of
the model name – in a narrow window they stay visible without sideways
scrolling. The Modelfile card folds open and shut via its heading
(“▾ einklappen” / “▸ ausklappen”); clicking “Modelfile” in the list unfolds it.

For the Modelfile the tool replaces blob paths:

```text
FROM /usr/share/ollama/.ollama/models/blobs/sha256-…   ← what /api/show returns
FROM qwen-test:7b                                      ← what the editor shows
```

The dependency view does **not** trust that comment but `details.parent_model`:
the `# FROM` hint always names the model itself (“this is how you build a copy”).
`GET /api/abhaengigkeiten?endpunkt=…&modell=…` asks `/api/show` for every model
of the endpoint in parallel and answers with `baut_auf`, `darauf_bauen`,
`geschwister` and `basis` (`modell`, `extern`, `datei` or `registry`). The result
is cached for 120 s and dropped after a create or delete.

A second `FROM` line (projector) is dropped and reported as a note –
`/api/create` accepts only one `FROM`.

## Rolling out models

Open a model, click “⇄ Ausrollen”, choose target and name. What happens depends on
what the model is built on; `details.parent_model` decides:

| Case | `parent_model` | What the tool does |
|---|---|---|
| pulled from a registry | empty | pulls the same model on the target (`/api/pull`) – that yields the same weights. Different target name: `/api/copy` afterwards |
| built from another model | a model name | `/api/create` with `FROM <parent>` plus parameters, template, system – weights come from the base, which must be present on the target (tick “Basis bei Bedarf ziehen” to pull it first) |
| built from a GGUF file | a file name | locked while the `gguf` feature is off (default). Once enabled: `/api/create` from a GGUF that sits **on the target** – nothing is copied |

A rollout never overwrites: if the target name is taken, the tool stops with a
message. Measured on 2026-11-16 against real endpoints: `codehamr-agent:latest`
on ollama-3 is built on `Julioa/Qwen3.8-27B-UD-Q3_K_XL` (rollable out wherever that
base is present), `bonsai-2:27b` carries `bonsai-2:27b-q2_0` as its parent, and
`qwen3.5:9b` has no parent at all – that one is pulled, not rebuilt.

For a model without a parent, rolling out needs no access to the source host's
files at all: the target pulls the same model from the registry itself, so the
weights arrive there identically and completely on their own.

### Rolling out GGUF models (feature, not normal operation)

If a model was built from a GGUF file, its weights exist only as a file – the
API does not hand them out. That case is rare and therefore **locked by
default**; it is enabled deliberately in the configuration:

```json
{"gguf": true}
```

or in `ollamaskope.conf`:

```text
gguf = ja
```

Then the tool builds the model on the target via `/api/create` from a GGUF path
that already exists **there** – nothing is copied. If the file lives elsewhere on
the target, enter it in the dialog under “GGUF-Pfad auf dem Ziel”. If it is
missing, Ollama answers with its error and the tool passes it through.

Weights never travel between two hosts: Ollama offers no endpoint for blob
downloads. Without file access (SSH/scp, a shared directory) a model built from
a GGUF file cannot be moved at all.

## Configuration (`config.json`)

```json
{
  "bind": "127.0.0.1",
  "port": 8090,
  "timeout": 25,
  "endpunkte": [
    {"id": "ollama-1", "name": "ollama-1 (10.0.0.24)",
     "url": "http://10.0.0.24:11434", "schreiben": true}
  ]
}
```

* `schreiben: false` locks create, delete and rolling out for that endpoint; the
UI disables the buttons and the server answers 403.
* Read-only by default: **ollama-2** (a model stays loaded there permanently,
  deleting it would break work in progress) and **ollama-3** (experiments in progress).
* Set `bind: 0.0.0.0` deliberately: there is **no login**.
* `"gguf": true` unlocks rolling out from GGUF files – off by default, because
  it is a special case, not normal operation (see below).

## Simple configuration (`ollamaskope.conf`)

If you would rather not maintain a JSON file, put a line-based file next to it –
`ollamaskope.conf` or `ollamaskope.env`, same layout:

```text
# comment, blank lines are ignored
bind = 0.0.0.0
port = 8090
timeout = 25

# name | url | rights       (rights: schreiben or lesen)
endpunkt = ollama-1 | http://10.0.0.24:11434 | schreiben
endpunkt = ollama-2    | http://10.0.0.81:11434 | lesen
endpunkt = http://10.0.0.79:11434        # name is taken from the address
```

* `=` or `:` separate key and value; `OLLAMASKOPE_BIND=…` is understood too.
  Unknown keys are an error **with the line number** – nothing is silently
  ignored.
* Lookup order: `--einfach PATH`, then `$OLLAMASKOPE_EINFACH`, otherwise
  `ollamaskope.conf` / `ollamaskope.env` next to `config.json`.
* **This file wins.** Its values override `bind`, `port` and `timeout`, its
  endpoints come first. Endpoints from `config.json` are appended as long as
  their URL is not already in the simple file.
* Endpoints from the file are marked “aus ollamaskope.conf” in the web dialog
  and cannot be removed there – they belong in the file. New endpoints from the
  web still go to `config.json`; when saving, file endpoints are not written
  into it (no duplicates).
* Check without starting: `python3 ollamaskope.py --pruefen` (shows source,
  bind, port and every endpoint with its rights; exit 3 on error).

## Why the Modelfile is split up

Ollama 0.40.14 no longer accepts the former `modelfile` field. Probe from
2026-11-16 against `10.0.0.24` – all three variants answer:

```json
{"error":"neither 'from' or 'files' was specified"}
```

Therefore `ollamaskope.py` parses the text itself and sends `model`, `from`,
`parameters`, `system`, `template`, `license`, `renderer`, `parser` and
`adapters`. Unknown directives (e.g. `MESSAGE`) are **not** silently dropped but
reported as an error.

## Limits

* `FROM` must be a model (or a file) that exists on the target server. A new
  model with the same weights is created via `FROM <existing model>`; nothing is
  downloaded. Rolling out therefore transfers a recipe, never a blob.
* No creating by uploading a local GGUF file.
* No login, no user management. Writing routes require the header
  `X-Anfrage: ollamaskope` (protection against foreign form pages), which is no
  substitute for authentication.
* `renderer`/`parser` are sent along; whether a given Ollama version honours them
  while creating has not been verified.

## Tests

The writing paths are tested against `tests/fake-ollama.py` – an Ollama stand-in
that rejects the raw `modelfile` field just like 0.40.14:

```bash
cd ~/ollamaskope
python3 -m unittest discover -s tests -v
```

There are 40 tests at the moment.

## License

Copyright (C) 2026 Olav Surawski (o-valo).

AGPL-3.0-or-later — see LICENSE.
Powered by AI

This project was developed with the support of AI-assisted tools for the code
changes and the documentation. The code, the tests and the architecture
decisions come from a human being who is responsible for them; remaining
defects are the responsibility of the project.

The models used are not named. The tools used have no influence on the licence:
the project remains under AGPL-3.0-or-later (see License).
