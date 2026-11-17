#!/usr/bin/env python3
"""Tests für ollamaskope gegen den Ollama-Ersatz in fake-ollama.py.

Aufruf:

    cd ~/ollamaskope && python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import Any

BASIS = Path(__file__).resolve().parent
WERKZEUG_DATEI = BASIS.parent / "ollamaskope.py"


def laden(pfad: Path, name: str) -> ModuleType:
    """Datei als Modul laden (Bindestrich im Dateinamen)."""
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, pfad)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{pfad} nicht ladbar")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


werkzeug = laden(WERKZEUG_DATEI, "ollama_sort")
fake_modul = laden(BASIS / "fake-ollama.py", "fake_ollama")


class EinfacheConfigTest(unittest.TestCase):
    """Die zeilenweise Konfiguration (ollamaskope.conf / ollamaskope.env)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.fake, cls.fake_thread, cls.fake_server = fake_modul.starten()
        cls.fake_url = f"http://127.0.0.1:{cls.fake_server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fake_server.shutdown()
        cls.fake_server.server_close()

    def setUp(self) -> None:
        self.fake.reset()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.basis = Path(self.tmpdir.name)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def schreibe(self, name: str, text: str) -> Path:
        pfad = self.basis / name
        pfad.write_text(text, encoding="utf-8")
        return pfad

    def test_zeilenweise_lesen(self) -> None:
        conf = self.schreibe(
            "ollamaskope.conf",
            """
# Kommentar
bind = 0.0.0.0
port: 8091
OLLAMASKOPE_TIMEOUT = 7,5
endpunkt = Werkstatt | http://127.0.0.1:11434/ | schreiben
endpunkt = http://10.0.0.81:11434
""",
        )
        daten = werkzeug.lade_einfache_config(conf)
        self.assertEqual(daten["bind"], "0.0.0.0")
        self.assertEqual(daten["port"], 8091)
        self.assertEqual(daten["timeout"], 7.5)
        self.assertEqual(
            [ep["name"] for ep in daten["endpunkte"]],
            ["Werkstatt", "10.0.0.81:11434"],
        )
        self.assertEqual(
            [ep["schreiben"] for ep in daten["endpunkte"]], [True, False]
        )
        self.assertEqual(daten["endpunkte"][0]["id"], "werkstatt")
        self.assertEqual(daten["endpunkte"][0]["url"], "http://127.0.0.1:11434")
        self.assertEqual(daten["endpunkte"][0]["quelle"], "conf")

    def test_alte_conf_datei_gilt_weiter(self) -> None:
        """Wer vor dem 17.11.2026 eingerichtet hat, hat noch ollama-sort.conf."""
        jsonpfad = self.schreibe(
            "config.json",
            json.dumps(
                {
                    "bind": "127.0.0.1",
                    "port": 8090,
                    "timeout": 25,
                    "endpunkte": [
                        {
                            "id": "json",
                            "name": "aus json",
                            "url": "http://10.0.0.9:11434",
                            "schreiben": True,
                        }
                    ],
                }
            ),
        )
        alt = self.schreibe("ollama-sort.conf", "port = 8098\n")
        config, _, einfachpfad = werkzeug.load_config(str(jsonpfad))
        self.assertEqual(einfachpfad, alt)
        self.assertEqual(config["port"], 8098)

    def test_unbekannter_schluessel_ist_ein_fehler(self) -> None:
        conf = self.schreibe("ollamaskope.conf", "bind = 127.0.0.1\nfarbe = blau\n")
        with self.assertRaises(werkzeug.ConfigError) as kontext:
            werkzeug.lade_einfache_config(conf)
        self.assertIn("farbe", str(kontext.exception))
        self.assertIn("2", str(kontext.exception))

    def test_endpunkt_ohne_url_ist_ein_fehler(self) -> None:
        conf = self.schreibe("ollamaskope.conf", "endpunkt = Werkstatt | schreiben\n")
        with self.assertRaises(werkzeug.ConfigError):
            werkzeug.lade_einfache_config(conf)

    def test_vorrang_und_ergaenzung(self) -> None:
        jsonpfad = self.schreibe(
            "config.json",
            json.dumps(
                {
                    "bind": "127.0.0.1",
                    "port": 8090,
                    "timeout": 25,
                    "endpunkte": [
                        {
                            "id": "json",
                            "name": "aus json",
                            "url": "http://10.0.0.5:11434",
                            "schreiben": True,
                        },
                        {
                            "id": "doppelt",
                            "name": "doppelt",
                            "url": "http://10.0.0.6:11434",
                            "schreiben": True,
                        },
                    ],
                }
            ),
        )
        self.schreibe(
            "ollamaskope.conf",
            "bind = 0.0.0.0\nport = 8099\n"
            "endpunkt = ollama-3 | http://10.0.0.6:11434 | lesen\n",
        )
        config, pfad, einfachpfad = werkzeug.load_config(str(jsonpfad))
        self.assertEqual(pfad, jsonpfad)
        self.assertEqual(einfachpfad, self.basis / "ollamaskope.conf")
        self.assertEqual(config["bind"], "0.0.0.0")
        self.assertEqual(config["port"], 8099)
        self.assertEqual(config["timeout"], 25)
        self.assertEqual(
            [ep["id"] for ep in config["endpunkte"]], ["ollama-3", "json"]
        )
        self.assertFalse(config["endpunkte"][0]["schreiben"])
        self.assertEqual(config["endpunkte"][0]["quelle"], "conf")
        self.assertEqual(config["endpunkte"][1]["quelle"], "config")

    def test_conf_endpunkte_bleiben_aus_config_json(self) -> None:
        jsonpfad = self.schreibe(
            "config.json",
            json.dumps(
                {
                    "bind": "127.0.0.1",
                    "port": 0,
                    "timeout": 5,
                    "endpunkte": [
                        {
                            "id": "fake",
                            "name": "fake",
                            "url": self.fake_url,
                            "schreiben": True,
                        }
                    ],
                }
            ),
        )
        self.schreibe(
            "ollamaskope.conf",
            "endpunkt = bestand | http://10.0.0.99:11434 | lesen\n",
        )
        config, _, _ = werkzeug.load_config(str(jsonpfad))
        self.assertEqual(
            [ep["id"] for ep in config["endpunkte"]], ["bestand", "fake"]
        )

        server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            werkzeug.make_handler(config, quiet=True, konfigpfad=jsonpfad),
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            basis = f"http://127.0.0.1:{server.server_address[1]}"
            with urllib.request.urlopen(basis + "/api/endpunkte", timeout=10) as a:
                geholt = json.loads(a.read().decode("utf-8"))["endpunkte"]
            self.assertEqual(
                [ep["quelle"] for ep in geholt], ["conf", "config"]
            )

            zusatz = f"http://localhost:{self.fake_server.server_address[1]}"
            anfrage = urllib.request.Request(
                basis + "/api/endpunkte",
                data=json.dumps(
                    {"name": "Neu", "url": zusatz, "schreiben": True}
                ).encode("utf-8"),
                method="POST",
            )
            anfrage.add_header("Content-Type", "application/json")
            anfrage.add_header("X-Anfrage", "ollamaskope")
            with urllib.request.urlopen(anfrage, timeout=10) as antwort:
                self.assertEqual(antwort.status, 200)
        finally:
            server.shutdown()
            server.server_close()

        gespeichert = json.loads(jsonpfad.read_text(encoding="utf-8"))
        self.assertEqual(
            [ep["id"] for ep in gespeichert["endpunkte"]], ["fake", "neu"]
        )
        self.assertNotIn("quelle", gespeichert["endpunkte"][0])

    def test_pruefen_startet_nichts(self) -> None:
        jsonpfad = self.schreibe(
            "config.json",
            json.dumps(
                {
                    "bind": "127.0.0.1",
                    "port": 8090,
                    "timeout": 25,
                    "endpunkte": [
                        {
                            "id": "x",
                            "name": "x",
                            "url": "http://10.0.0.9:11434",
                            "schreiben": False,
                        }
                    ],
                }
            ),
        )
        conf = self.schreibe("ollamaskope.conf", "port = 8091\n")
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            code = werkzeug.main(
                ["--pruefen", "--config", str(jsonpfad), "--einfach", str(conf)]
            )
        self.assertEqual(code, 0)
        ausgabe = puffer.getvalue()
        self.assertIn("8091", ausgabe)
        self.assertIn("nur lesen", ausgabe)

    def test_kaputte_conf_meldet_zeile(self) -> None:
        jsonpfad = self.schreibe(
            "config.json",
            json.dumps(
                {
                    "bind": "127.0.0.1",
                    "port": 8090,
                    "timeout": 25,
                    "endpunkte": [
                        {
                            "id": "x",
                            "name": "x",
                            "url": "http://10.0.0.9:11434",
                            "schreiben": False,
                        }
                    ],
                }
            ),
        )
        conf = self.schreibe("ollamaskope.conf", "tolleranz = 3\n")
        puffer = io.StringIO()
        with contextlib.redirect_stderr(puffer):
            code = werkzeug.main(
                ["--pruefen", "--config", str(jsonpfad), "--einfach", str(conf)]
            )
        self.assertEqual(code, 3)
        self.assertIn("tolleranz", puffer.getvalue())


class AusrollTest(unittest.TestCase):
    """Ein Modell von einem Endpunkt auf einem anderen nachbauen."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.quelle_fake, cls.quelle_thread, cls.quelle_server = fake_modul.starten()
        cls.ziel_fake, cls.ziel_thread, cls.ziel_server = fake_modul.starten()
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.konfigpfad = Path(cls.tmpdir.name) / "config.json"
        config = {
            "bind": "127.0.0.1",
            "port": 0,
            "timeout": 5,
            "endpunkte": [
                {
                    "id": "quelle",
                    "name": "Quelle",
                    "url": f"http://127.0.0.1:{cls.quelle_server.server_address[1]}",
                    "schreiben": True,
                },
                {
                    "id": "ziel",
                    "name": "Ziel",
                    "url": f"http://127.0.0.1:{cls.ziel_server.server_address[1]}",
                    "schreiben": True,
                },
                {
                    "id": "ziel-lesen",
                    "name": "Ziel (nur lesen)",
                    "url": f"http://127.0.0.1:{cls.ziel_server.server_address[1]}",
                    "schreiben": False,
                },
            ],
        }
        cls.konfigpfad.write_text(json.dumps(config, indent=2), encoding="utf-8")
        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            werkzeug.make_handler(config, quiet=True, konfigpfad=cls.konfigpfad),
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.basis = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        for server in (cls.quelle_server, cls.ziel_server):
            server.shutdown()
            server.server_close()
        cls.tmpdir.cleanup()

    def setUp(self) -> None:
        self.quelle_fake.reset()
        self.ziel_fake.reset()
        werkzeug.graph_verwerfen("quelle")
        werkzeug.graph_verwerfen("ziel")

    def ausrollen(self, **daten: Any) -> tuple[int, str]:
        rumpf = {"quelle": "quelle", "ziel": "ziel", "modell": "klein:latest"}
        rumpf.update(daten)
        anfrage = urllib.request.Request(
            self.basis + "/api/ausrollen",
            data=json.dumps(rumpf).encode("utf-8"),
            method="POST",
        )
        anfrage.add_header("Content-Type", "application/json")
        anfrage.add_header("X-Anfrage", "ollamaskope")
        try:
            with urllib.request.urlopen(anfrage, timeout=15) as antwort:
                return antwort.status, antwort.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    def zeilen(self, text: str) -> list[dict[str, Any]]:
        return [json.loads(zeile) for zeile in text.splitlines() if zeile.strip()]

    def test_ausroll_baut_das_rezept_nach(self) -> None:
        code, text = self.ausrollen(name="klein-kopie")
        self.assertEqual(code, 200, text)
        self.assertEqual(self.zeilen(text)[-1]["status"], "success")

        self.assertEqual(len(self.ziel_fake.erzeugt), 1)
        gesendet = self.ziel_fake.erzeugt[0]
        self.assertNotIn("modelfile", gesendet)
        self.assertEqual(gesendet["model"], "klein-kopie")
        self.assertEqual(gesendet["from"], "qwen-test:7b")
        self.assertEqual(gesendet["parameters"]["num_ctx"], 32768)
        self.assertEqual(gesendet["parameters"]["stop"], ["<|ende|>"])
        self.assertEqual(gesendet["system"], "Du bist ein Testmodell.")
        self.assertEqual(gesendet["template"], "{{ .Prompt }}")
        self.assertIn("klein-kopie", self.ziel_fake.modelle)
        self.assertEqual(self.ziel_fake.zieht, [])
        self.assertEqual(self.quelle_fake.erzeugt, [])

    def test_ausroll_ohne_namen_nimmt_denselben(self) -> None:
        code, text = self.ausrollen()
        # „klein:latest“ gibt es auf dem Ziel schon – das muss auffallen.
        self.assertEqual(code, 400)
        self.assertIn("gibt es auf dem Ziel schon", json.loads(text)["fehler"])
        self.assertEqual(self.ziel_fake.erzeugt, [])

    def test_ausroll_aus_datei_gebautes_modell_wird_erklaert(self) -> None:
        code, text = self.ausrollen(modell="qwen-test:7b", name="qwen-kopie")
        self.assertEqual(code, 400)
        meldung = json.loads(text)["fehler"]
        self.assertIn("aus einer Datei", meldung)
        self.assertIn("GGUF", meldung)
        self.assertEqual(self.ziel_fake.erzeugt, [])
        self.assertEqual(self.ziel_fake.zieht, [])

    def test_ausroll_aus_der_registry_wird_gezogen(self) -> None:
        del self.ziel_fake.modelle["registry:7b"]
        code, text = self.ausrollen(modell="registry:7b", name="registry:7b")
        self.assertEqual(code, 200, text)
        self.assertEqual(self.ziel_fake.zieht, ["registry:7b"])
        self.assertEqual(self.ziel_fake.erzeugt, [])
        self.assertEqual(self.ziel_fake.kopiert, [])
        self.assertIn("registry:7b", self.ziel_fake.modelle)
        self.assertEqual(self.zeilen(text)[-1]["status"], "success")

    def test_ausroll_aus_der_registry_unter_neuem_namen(self) -> None:
        code, text = self.ausrollen(modell="registry:7b", name="registry-kopie")
        self.assertEqual(code, 200, text)
        self.assertEqual(self.ziel_fake.zieht, ["registry:7b"])
        self.assertEqual(self.ziel_fake.kopiert, [("registry:7b", "registry-kopie")])
        self.assertIn("registry-kopie", self.ziel_fake.modelle)
        self.assertEqual(self.zeilen(text)[-1]["status"], "success")

    def test_ausroll_braucht_schreibrecht_am_ziel(self) -> None:
        code, text = self.ausrollen(ziel="ziel-lesen", name="klein-kopie")
        self.assertEqual(code, 403, text)
        self.assertEqual(self.ziel_fake.erzeugt, [])

    def test_ausroll_am_selben_endpunkt_ist_ein_fehler(self) -> None:
        code, text = self.ausrollen(ziel="quelle", name="klein-kopie")
        self.assertEqual(code, 400)
        self.assertIn("selbe Endpunkt", json.loads(text)["fehler"])

    def test_ausroll_meldet_fehlende_basis(self) -> None:
        del self.ziel_fake.modelle["qwen-test:7b"]
        code, text = self.ausrollen(name="klein-kopie")
        self.assertEqual(code, 400)
        self.assertIn("liegt nicht auf dem Ziel", json.loads(text)["fehler"])
        self.assertEqual(self.ziel_fake.zieht, [])
        self.assertEqual(self.ziel_fake.erzeugt, [])

    def test_ausroll_zieht_fehlende_basis_auf_wunsch(self) -> None:
        del self.ziel_fake.modelle["qwen-test:7b"]
        code, text = self.ausrollen(name="klein-kopie", basis_ziehen=True)
        self.assertEqual(code, 200, text)
        self.assertEqual(self.ziel_fake.zieht, ["qwen-test:7b"])
        self.assertIn("qwen-test:7b", self.ziel_fake.modelle)
        self.assertEqual(self.ziel_fake.erzeugt[0]["from"], "qwen-test:7b")
        self.assertEqual(self.zeilen(text)[-1]["status"], "success")


class AusrollGgufTest(unittest.TestCase):
    """Ausrollen aus einer GGUF-Datei: Feature, nur mit `gguf: true`.

    Kopiert wird nichts – gebaut wird aus der Datei, die auf dem Ziel liegt.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.quelle_fake, cls.quelle_thread, cls.quelle_server = fake_modul.starten()
        cls.ziel_fake, cls.ziel_thread, cls.ziel_server = fake_modul.starten()
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.konfigpfad = Path(cls.tmpdir.name) / "config.json"
        config = {
            "bind": "127.0.0.1",
            "port": 0,
            "timeout": 5,
            "gguf": True,
            "endpunkte": [
                {
                    "id": "quelle",
                    "name": "Quelle",
                    "url": f"http://127.0.0.1:{cls.quelle_server.server_address[1]}",
                    "schreiben": True,
                },
                {
                    "id": "ziel",
                    "name": "Ziel",
                    "url": f"http://127.0.0.1:{cls.ziel_server.server_address[1]}",
                    "schreiben": True,
                },
            ],
        }
        cls.konfigpfad.write_text(json.dumps(config, indent=2), encoding="utf-8")
        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            werkzeug.make_handler(config, quiet=True, konfigpfad=cls.konfigpfad),
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.basis = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        for server in (cls.quelle_server, cls.ziel_server):
            server.shutdown()
            server.server_close()
        cls.tmpdir.cleanup()

    def setUp(self) -> None:
        self.quelle_fake.reset()
        self.ziel_fake.reset()
        werkzeug.graph_verwerfen("ziel")

    def ausrollen(self, **daten: Any) -> tuple[int, str]:
        rumpf = {"quelle": "quelle", "ziel": "ziel", "modell": "qwen-test:7b"}
        rumpf.update(daten)
        anfrage = urllib.request.Request(
            self.basis + "/api/ausrollen",
            data=json.dumps(rumpf).encode("utf-8"),
            method="POST",
        )
        anfrage.add_header("Content-Type", "application/json")
        anfrage.add_header("X-Anfrage", "ollamaskope")
        try:
            with urllib.request.urlopen(anfrage, timeout=15) as antwort:
                return antwort.status, antwort.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    def test_gguf_baut_aus_der_datei_des_elternteils(self) -> None:
        code, text = self.ausrollen(name="qwen-datei")
        self.assertEqual(code, 200, text)
        self.assertEqual(len(self.ziel_fake.erzeugt), 1)
        gesendet = self.ziel_fake.erzeugt[0]
        self.assertEqual(gesendet["model"], "qwen-datei")
        self.assertEqual(gesendet["from"], "qwen-test-base.gguf")
        self.assertEqual(gesendet["system"], "Du bist ein Testmodell.")
        self.assertEqual(self.ziel_fake.zieht, [])
        self.assertIn("qwen-datei", self.ziel_fake.modelle)

    def test_gguf_nimmt_den_pfad_auf_dem_ziel(self) -> None:
        code, text = self.ausrollen(
            name="qwen-datei", basis_datei="/srv/gguf/qwen-test-base.gguf"
        )
        self.assertEqual(code, 200, text)
        self.assertEqual(
            self.ziel_fake.erzeugt[0]["from"], "/srv/gguf/qwen-test-base.gguf"
        )

    def test_gguf_pfad_muss_wie_eine_datei_aussehen(self) -> None:
        code, text = self.ausrollen(name="qwen-datei", basis_datei="nur-ein-name")
        self.assertEqual(code, 400)
        self.assertIn("GGUF-Datei", json.loads(text)["fehler"])
        self.assertEqual(self.ziel_fake.erzeugt, [])

    def test_gguf_ohne_freigabe_bleibt_gesperrt(self) -> None:
        self.ziel_fake.reset()
        config = {**werkzeug.load_config(str(self.konfigpfad))[0]}
        config["gguf"] = False
        self.assertFalse(config["gguf"])


class WerkzeugTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fake, cls.fake_thread, cls.fake_server = fake_modul.starten()
        port = cls.fake_server.server_address[1]
        fake_url = f"http://127.0.0.1:{port}"
        cls.fake_url = fake_url
        cls.fake_localhost = f"http://localhost:{port}"
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.konfigpfad = Path(cls.tmpdir.name) / "config.json"
        config = {
            "bind": "127.0.0.1",
            "port": 0,
            "timeout": 5,
            "endpunkte": [
                {
                    "id": "fake",
                    "name": "fake",
                    "url": fake_url,
                    "schreiben": True,
                },
                {
                    "id": "nurlesen",
                    "name": "nurlesen",
                    "url": fake_url,
                    "schreiben": False,
                },
            ],
        }
        cls.konfigpfad.write_text(json.dumps(config, indent=2), encoding="utf-8")
        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            werkzeug.make_handler(config, quiet=True, konfigpfad=cls.konfigpfad),
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.basis = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.fake_server.shutdown()
        cls.fake_server.server_close()
        cls.tmpdir.cleanup()

    def setUp(self) -> None:
        self.fake.reset()
        werkzeug.graph_verwerfen("fake")
        # Protokoll der Ladevorgänge nicht in den Projektordner schreiben.
        werkzeug.LADEN_LOG = Path(self.tmpdir.name) / "laden.log"

    def ruf(
        self,
        pfad: str,
        methode: str = "GET",
        daten: dict[str, Any] | None = None,
        kopf: bool = True,
    ) -> tuple[int, str]:
        rumpf = None if daten is None else json.dumps(daten).encode("utf-8")
        anfrage = urllib.request.Request(self.basis + pfad, data=rumpf, method=methode)
        if daten is not None:
            anfrage.add_header("Content-Type", "application/json")
        if kopf:
            anfrage.add_header("X-Anfrage", "ollamaskope")
        try:
            with urllib.request.urlopen(anfrage, timeout=10) as antwort:
                return antwort.status, antwort.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    # -- Anzeigen ------------------------------------------------------

    def test_modelle_und_geladen(self) -> None:
        code, text = self.ruf("/api/modelle?endpunkt=fake")
        self.assertEqual(code, 200)
        daten = json.loads(text)
        self.assertEqual(daten["version"], "9.9.9-fake")
        namen = {modell["name"] for modell in daten["modelle"]}
        self.assertEqual(namen, {"qwen-test:7b", "klein:latest", "registry:7b"})
        self.assertEqual([eintrag["name"] for eintrag in daten["geladen"]], ["qwen-test:7b"])

    def test_unbekannter_endpunkt(self) -> None:
        code, text = self.ruf("/api/modelle?endpunkt=gibtsnicht")
        self.assertEqual(code, 400)
        self.assertIn("Unbekannter Endpunkt", json.loads(text)["fehler"])

    def test_endpunktliste_ohne_schreibrechte_zu_verraten(self) -> None:
        code, text = self.ruf("/api/endpunkte")
        self.assertEqual(code, 200)
        endpunkte = {eintrag["id"]: eintrag for eintrag in json.loads(text)["endpunkte"]}
        self.assertTrue(endpunkte["fake"]["schreiben"])
        self.assertFalse(endpunkte["nurlesen"]["schreiben"])

    # -- Modelfile bauen ----------------------------------------------

    def test_modelfile_ersetzt_blob_durch_modellnamen(self) -> None:
        code, text = self.ruf(
            "/api/modelfile", "POST", {"endpunkt": "fake", "modell": "qwen-test:7b"}
        )
        self.assertEqual(code, 200)
        daten = json.loads(text)
        modelfile = daten["modelfile"]
        self.assertIn("FROM qwen-test:7b", modelfile)
        self.assertNotIn("blobs/", modelfile)
        self.assertEqual(modelfile.count("FROM "), 1)
        self.assertIn("PARAMETER num_ctx 32768", modelfile)
        self.assertIn("Du bist ein Testmodell.", modelfile)
        self.assertGreaterEqual(len(daten["warnungen"]), 2)

    # -- Erzeugen ------------------------------------------------------

    def test_erzeugen_sendet_strukturierte_felder(self) -> None:
        modelfile = (
            "FROM qwen-test:7b\n"
            "PARAMETER num_ctx 32768\n"
            'PARAMETER stop "<|ende|>"\n'
            'SYSTEM """Du bist eine Kopie."""\n'
            "TEMPLATE {{ .Prompt }}\n"
            "RENDERER qwen3.5\n"
        )
        code, text = self.ruf(
            "/api/erzeugen",
            "POST",
            {"endpunkt": "fake", "name": "kopie:test", "modelfile": modelfile},
        )
        self.assertEqual(code, 200)
        zeilen = [json.loads(zeile) for zeile in text.splitlines() if zeile.strip()]
        self.assertEqual(zeilen[-1]["status"], "success")

        self.assertEqual(len(self.fake.erzeugt), 1)
        gesendet = self.fake.erzeugt[0]
        self.assertNotIn("modelfile", gesendet)
        self.assertEqual(gesendet["model"], "kopie:test")
        self.assertEqual(gesendet["from"], "qwen-test:7b")
        self.assertEqual(gesendet["parameters"]["num_ctx"], 32768)
        self.assertEqual(gesendet["parameters"]["stop"], ["<|ende|>"])
        self.assertEqual(gesendet["system"], "Du bist eine Kopie.")
        self.assertEqual(gesendet["template"], "{{ .Prompt }}")
        self.assertEqual(gesendet["renderer"], "qwen3.5")

        code, text = self.ruf("/api/modelle?endpunkt=fake")
        namen = {modell["name"] for modell in json.loads(text)["modelle"]}
        self.assertIn("kopie:test", namen)

    def test_erzeugen_ohne_from(self) -> None:
        code, text = self.ruf(
            "/api/erzeugen",
            "POST",
            {"endpunkt": "fake", "name": "ohne:from", "modelfile": "PARAMETER num_ctx 4096\n"},
        )
        self.assertEqual(code, 400)
        self.assertIn("kein FROM", json.loads(text)["fehler"])
        self.assertEqual(self.fake.erzeugt, [])

    def test_erzeugen_meldet_unbekannte_anweisung(self) -> None:
        code, text = self.ruf(
            "/api/erzeugen",
            "POST",
            {
                "endpunkt": "fake",
                "name": "quatsch:test",
                "modelfile": "FROM qwen-test:7b\nQUATSCH 1\n",
            },
        )
        self.assertEqual(code, 400)
        self.assertIn("QUATSCH", json.loads(text)["fehler"])

    def test_erzeugen_gesperrt_bei_schreibschutz(self) -> None:
        code, text = self.ruf(
            "/api/erzeugen",
            "POST",
            {
                "endpunkt": "nurlesen",
                "name": "gesperrt:test",
                "modelfile": "FROM qwen-test:7b\n",
            },
        )
        self.assertEqual(code, 403)
        self.assertIn("schreibgeschützt", json.loads(text)["fehler"])
        self.assertEqual(self.fake.erzeugt, [])

    # -- Löschen -------------------------------------------------------

    def test_loeschen_braucht_bestaetigung(self) -> None:
        code, text = self.ruf(
            "/api/loeschen",
            "POST",
            {"endpunkt": "fake", "modell": "klein:latest", "bestaetigung": "klein"},
        )
        self.assertEqual(code, 400)
        self.assertIn("Bestätigung", json.loads(text)["fehler"])
        self.assertIn("klein:latest", self.fake.modelle)
        self.assertEqual(self.fake.geloescht, [])

    def test_loeschen_gesperrt_bei_schreibschutz(self) -> None:
        code, text = self.ruf(
            "/api/loeschen",
            "POST",
            {
                "endpunkt": "nurlesen",
                "modell": "klein:latest",
                "bestaetigung": "klein:latest",
            },
        )
        self.assertEqual(code, 403)
        self.assertIn("klein:latest", self.fake.modelle)

    def test_loeschen_mit_bestaetigung(self) -> None:
        code, text = self.ruf(
            "/api/loeschen",
            "POST",
            {
                "endpunkt": "fake",
                "modell": "klein:latest",
                "bestaetigung": "klein:latest",
            },
        )
        self.assertEqual(code, 200)
        self.assertTrue(json.loads(text)["ok"])
        self.assertNotIn("klein:latest", self.fake.modelle)
        self.assertEqual(self.fake.geloescht, ["klein:latest"])

    # -- Laden und Entladen --------------------------------------------

    def test_laden_und_entladen(self) -> None:
        code, text = self.ruf(
            "/api/laden", "POST", {"endpunkt": "fake", "modell": "klein:latest"}
        )
        self.assertEqual(code, 200, text)
        daten = json.loads(text)
        self.assertTrue(daten["geladen"])
        self.assertEqual(daten["grund"], "load")
        self.assertEqual(self.fake.ladeauftraege[-1]["keep_alive"], "30m")
        self.assertIn("klein:latest", self.fake.geladen)

        code, text = self.ruf("/api/modelle?endpunkt=fake")
        geladen = [eintrag["name"] for eintrag in json.loads(text)["geladen"]]
        self.assertIn("klein:latest", geladen)

        code, text = self.ruf(
            "/api/entladen", "POST", {"endpunkt": "fake", "modell": "klein:latest"}
        )
        self.assertEqual(code, 200, text)
        daten = json.loads(text)
        self.assertFalse(daten["geladen"])
        self.assertEqual(daten["grund"], "unload")
        self.assertEqual(self.fake.ladeauftraege[-1]["keep_alive"], 0)
        self.assertNotIn("klein:latest", self.fake.geladen)

    def test_laden_und_entladen_landet_im_protokoll(self) -> None:
        """Das Protokoll nennt Endpunkt, Modell, Dauer und done_reason."""
        protokoll = Path(werkzeug.LADEN_LOG)
        protokoll.write_text("", encoding="utf-8")
        for pfad in ("/api/laden", "/api/entladen"):
            code, text = self.ruf(
                pfad, "POST", {"endpunkt": "fake", "modell": "klein:latest"}
            )
            self.assertEqual(code, 200, text)
        zeilen = protokoll.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(zeilen), 2, zeilen)
        laden, entladen = (zeile.split("\t") for zeile in zeilen)
        self.assertEqual(len(laden), 7, zeilen[0])
        self.assertEqual(laden[1], "laden")
        self.assertEqual(laden[2], "fake")
        self.assertEqual(laden[3], self.fake_url)
        self.assertEqual(laden[4], "klein:latest")
        self.assertTrue(laden[5].endswith("s"), laden[5])
        self.assertEqual(laden[6], "ok done_reason=load")
        self.assertEqual(entladen[1], "entladen")
        self.assertEqual(entladen[6], "ok done_reason=unload")

    # -- Endpunkte eintragen und entfernen ---------------------------

    def test_endpunkt_hinzufuegen_und_entfernen(self) -> None:
        code, text = self.ruf(
            "/api/endpunkte",
            "POST",
            {"name": "Werkstatt", "url": self.fake_localhost, "schreiben": True},
        )
        self.assertEqual(code, 200, text)
        daten = json.loads(text)
        self.assertEqual(daten["endpunkt"]["id"], "werkstatt")
        self.assertEqual(daten["version"], "9.9.9-fake")
        self.assertTrue(daten["endpunkt"]["schreiben"])

        gespeichert = json.loads(self.konfigpfad.read_text(encoding="utf-8"))
        self.assertIn("werkstatt", [ep["id"] for ep in gespeichert["endpunkte"]])

        code, text = self.ruf("/api/endpunkte")
        self.assertIn("werkstatt", [ep["id"] for ep in json.loads(text)["endpunkte"]])

        code, text = self.ruf("/api/endpunkte/entfernen", "POST", {"id": "werkstatt"})
        self.assertEqual(code, 200, text)
        self.assertEqual(json.loads(text)["entfernt"]["id"], "werkstatt")
        gespeichert = json.loads(self.konfigpfad.read_text(encoding="utf-8"))
        self.assertNotIn("werkstatt", [ep["id"] for ep in gespeichert["endpunkte"]])

    def test_endpunkt_unerreichbar_wird_abgelehnt(self) -> None:
        code, text = self.ruf(
            "/api/endpunkte",
            "POST",
            {"name": "Tot", "url": "http://127.0.0.1:1", "schreiben": False},
        )
        self.assertEqual(code, 400)
        self.assertIn("antwortet nicht", json.loads(text)["fehler"])
        gespeichert = json.loads(self.konfigpfad.read_text(encoding="utf-8"))
        self.assertNotIn("tot", [ep["id"] for ep in gespeichert["endpunkte"]])

    # -- Abhängigkeiten ------------------------------------------------

    def test_abhaengigkeiten_kinder_und_eltern(self) -> None:
        code, text = self.ruf("/api/abhaengigkeiten?endpunkt=fake&modell=qwen-test:7b")
        self.assertEqual(code, 200)
        daten = json.loads(text)
        self.assertEqual(daten["basis"], "datei")
        self.assertEqual(daten["baut_auf"], [])
        self.assertEqual([kind["modell"] for kind in daten["darauf_bauen"]], ["klein:latest"])
        self.assertEqual(daten["geprueft"], 3)

        code, text = self.ruf("/api/abhaengigkeiten?endpunkt=fake&modell=klein:latest")
        self.assertEqual(code, 200)
        daten = json.loads(text)
        self.assertEqual(daten["basis"], "modell")
        self.assertEqual([eintrag["modell"] for eintrag in daten["baut_auf"]], ["qwen-test:7b"])
        self.assertTrue(daten["baut_auf"][0]["vorhanden"])
        self.assertEqual(daten["darauf_bauen"], [])

    def test_abhaengigkeiten_unbekannter_endpunkt(self) -> None:
        code, text = self.ruf(
            "/api/abhaengigkeiten?endpunkt=gibtsnicht&modell=klein:latest"
        )
        self.assertEqual(code, 400)
        self.assertIn("Unbekannter Endpunkt", json.loads(text)["fehler"])

    # -- Oberfläche ----------------------------------------------------

    def test_oberflaeche_hat_sprach_und_themschalter(self) -> None:
        code, text = self.ruf("/")
        self.assertEqual(code, 200)
        self.assertIn('id="sprache"', text)
        self.assertIn('id="thema"', text)
        self.assertIn("data-i18n", text)
        code, js = self.ruf("/app.js")
        self.assertEqual(code, 200)
        self.assertIn("const TEXTE = {", js)
        self.assertIn("function spracheUmschalten", js)
        self.assertIn("function themaUmschalten", js)
        self.assertIn('"ollamaskope-thema"', js)

    # -- Schutz --------------------------------------------------------

    def test_schreibende_wege_ohne_kopf_gesperrt(self) -> None:
        code, text = self.ruf(
            "/api/loeschen",
            "POST",
            {
                "endpunkt": "fake",
                "modell": "klein:latest",
                "bestaetigung": "klein:latest",
            },
            kopf=False,
        )
        self.assertEqual(code, 403)
        self.assertIn("X-Anfrage", json.loads(text)["fehler"])
        self.assertIn("klein:latest", self.fake.modelle)


if __name__ == "__main__":
    unittest.main()
