"use strict";

// ---------------------------------------------------------------------------
// Sprache und Design
// ---------------------------------------------------------------------------
// Deutsch ist die Quelle; jeder sichtbare Text steht unter einem Schlüssel.
// Neue Texte also immer in beide Tabellen unten – und im HTML als data-i18n.
const TEXTE = {
  de: {
    "kopf.unter": "Das Fernrohr für Ollama: Modelle ansehen, Modelfile bauen, laden, erzeugen und löschen.",
    "kopf.endpunkt": "Endpunkt",
    "kopf.endpunktNeu": "＋ Endpunkt",
    "kopf.aktualisieren": "Aktualisieren",
    "schalter.sprache": "Sprache umschalten: Deutsch / English",
    "schalter.hell": "Helles Design einschalten",
    "schalter.dunkel": "Dunkles Design einschalten",
    "karte.ausklappen": "▸ ausklappen",
    "karte.einklappen": "▾ einklappen",
    "modelle.titel": "Modelle",
    "modelle.aktionen": "Aktionen",
    "modelle.filter": "filtern …",
    "spalte.modell": "Modell",
    "spalte.modellTitel": "Alphabetisch sortieren",
    "spalte.groesse": "Größe",
    "spalte.groesseTitel": "Nach Größe sortieren",
    "spalte.familie": "Familie",
    "spalte.familieTitel": "Nach Familie sortieren",
    "spalte.parameter": "Parameter",
    "spalte.parameterTitel": "Nach Parameterzahl sortieren",
    "spalte.quant": "Quant",
    "spalte.quantTitel": "Nach Quantisierung sortieren",
    "spalte.geaendert": "geändert",
    "spalte.geaendertTitel": "Nach Änderungsdatum sortieren",
    "modelfile.titel": "Modelfile",
    "modelfile.ausrollen": "⇄ Ausrollen",
    "modelfile.loeschen": "🗑 Löschen",
    "modelfile.kopieren": "Kopieren",
    "modelfile.datei": "Als Datei",
    "modelfile.hinweisLeer": "Bei einem Modell auf „Modelfile“ klicken, um es hier zu bearbeiten.",
    "modelfile.platzhalter": 'FROM qwen3.5:9b\nPARAMETER num_ctx 32768\nSYSTEM """Du bist …"""',
    "modelfile.neuerName": "Neuer Modellname",
    "modelfile.namePlatzhalter": "mein-modell:latest",
    "modelfile.erzeugen": "Modell erzeugen",
    "modelfile.schreibHinweis": 'Dieser Endpunkt ist schreibgeschützt. Erzeugen und Löschen sind gesperrt – in <code>config.json</code> beim Endpunkt <code>"schreiben": true</code> setzen.',
    "ep.titel": "Endpunkte",
    "ep.hinweis": "Wird in config.json gespeichert und gilt sofort.",
    "ep.neu": "Neuen Endpunkt eintragen",
    "ep.name": "Name",
    "ep.namePlatzhalter": "z. B. werkstatt",
    "ep.url": "URL",
    "ep.urlPlatzhalter": "http://10.0.0.50:11434",
    "ep.schreiben": "Erzeugen und Löschen auf diesem Endpunkt erlauben",
    "ep.schliessen": "Schließen",
    "ep.eintragen": "Eintragen",
    "ep.abbrechen": "Abbrechen",
    "ep.wegTitel": "Endpunkt entfernen?",
    "ep.wegText": "wird aus der Liste und aus config.json entfernt. Modelle auf dem Endpunkt bleiben unberührt.",
    "ep.wegJa": "Ja, entfernen",
    "ep.ausConf": "aus ollamaskope.conf",
    "ep.entfernen": "Entfernen",
    "ep.nurLesen": " · nur lesen",
    "ep.hinweisConf": "Endpunkte aus ollamaskope.conf stehen fest – dort bearbeiten. Neue landen in config.json.",
    "ep.nameUrlFehlt": "Name und URL angeben.",
    "ep.eingetragen": "{0} eingetragen (Ollama {1}).",
    "ep.entfernt": "Endpunkt entfernt.",
    "abh.titel": "Abhängigkeiten",
    "abh.status": "prüfe die Modelfiles …",
    "abh.loeschen": "Dieses Modell löschen",
    "abh.schliessen": "Schließen",
    "abh.pruefe": "prüfe die Modelfiles aller Modelle …",
    "abh.bautAuf": "baut auf",
    "abh.darauf": "darauf bauen auf",
    "abh.geschwister": "Geschwister (gleiche Basis)",
    "abh.keinElternteil": "Kein Elternteil eingetragen.",
    "abh.keinKind": "Kein anderes Modell baut darauf auf.",
    "abh.keine": "Keine.",
    "abh.ausDatei": 'Gebaut aus einer Datei: <code>{0}</code> – kein Modell auf diesem Endpunkt.',
    "abh.ausRegistry": "Aus der Registry geladen – kein Elternteil eingetragen.",
    "abh.geprueft": "{0} Modelle geprüft ({1})",
    "abh.zwischen": "zwischengespeichert",
    "abh.jetzt": "gerade eben",
    "abh.ohneAntwort": " · {0} ohne Antwort",
    "abh.nichtLadbar": "Nicht ladbar: {0}",
    "abh.nichtDa": "nicht auf diesem Endpunkt",
    "loeschen.titel": "Modell wirklich löschen?",
    "loeschen.text1": "Das Modell",
    "loeschen.text2": "wird mit seinen Dateien vom Endpunkt entfernt. Das lässt sich nicht rückgängig machen.",
    "loeschen.abbrechen": "Abbrechen",
    "loeschen.ja": "Ja, löschen",
    "loeschen.ok": "{0} gelöscht.",
    "ausroll.titel": "Modell ausrollen",
    "ausroll.von": "von",
    "ausroll.hinweis": "Übertragen wird das Rezept – Basis, Parameter, Template und Systemtext. Die Gewichte bleiben, wo sie sind: die Basis muss auf dem Ziel liegen.",
    "ausroll.ziel": "Ziel-Endpunkt",
    "ausroll.name": "Name auf dem Ziel",
    "ausroll.basis": "Fehlende Basis dort ziehen (lädt sie aus der Registry, kann mehrere GB sein)",
    "ausroll.datei": "GGUF-Pfad auf dem Ziel",
    "ausroll.dateiOptional": "(nur GGUF-Modelle, optional)",
    "ausroll.dateiPlatzhalter": "leer lassen, wenn die Datei dort gleich heißt",
    "ausroll.abbrechen": "Abbrechen",
    "ausroll.ja": "Ausrollen",
    "ausroll.keinZiel": "Kein anderer Endpunkt mit Schreibrecht eingetragen.",
    "ausroll.nameFehlt": "Bitte einen Namen für das Ziel angeben.",
    "ausroll.laeuft": "Ausrollen: {0} von {1} nach {2} als {3} …",
    "ausroll.ok": "{0} liegt jetzt auf {1}.",
    "status.laedt": "lädt …",
    "status.erreichbar": "erreichbar · Ollama {0} · {1} Modelle",
    "status.fehler": "nicht erreichbar",
    "liste.keinTreffer": "Kein Modell passt zum Filter.",
    "liste.leer": "Dieser Endpunkt meldet keine Modelle.",
    "aktion.laden": "Laden",
    "aktion.entladen": "Entladen",
    "aktion.ladenTitel": "In den Speicher laden (30 Minuten)",
    "aktion.entladenTitel": "Aus dem Speicher nehmen",
    "aktion.entladenLeer": "Liegt nicht im Speicher – nichts zu entladen",
    "aktion.geladen": "geladen",
    "aktion.abhTitel": "Abhängigkeiten anzeigen",
    "schreib.hinweis": 'Nur lesen: dieser Endpunkt steht in config.json auf "schreiben": false – Erzeugen und Löschen sind gesperrt.',
    "titel.loeschen": "Modell löschen",
    "titel.gesperrt": "Endpunkt ist schreibgeschützt (config.json: schreiben=false)",
    "titel.ausrollen": "Dieses Modell auf einem anderen Endpunkt nachbauen",
    "titel.ausrollenKeinZiel": "Kein anderer Endpunkt mit Schreibrecht eingetragen",
    "toast.laedt": "{0} wird geladen …",
    "toast.entlaedt": "{0} wird entladen …",
    "toast.geladen": "{0} ist geladen (30 Minuten).",
    "toast.entladen": "{0} entladen.",
    "mf.laedt": "lade Modelfile …",
    "mf.hinweis": "Bearbeiten und mit neuem Namen erzeugen. FROM zeigt auf ein Modell, das auf dem Endpunkt liegt.",
    "mf.fehler": "Modelfile nicht ladbar: {0}",
    "erz.gesperrt": "Dieser Endpunkt ist schreibgeschützt.",
    "erz.nameFehlt": "Bitte einen Modellnamen angeben.",
    "erz.leer": "Das Modelfile ist leer.",
    "erz.laeuft": "Erzeuge {0} auf {1} …",
    "erz.fertig": "fertig",
    "erz.ok": "Modell {0} erzeugt.",
    "erz.ohneErfolg": "Ohne Erfolgsmeldung beendet – Log prüfen.",
    "erz.fehler": "Fehler: {0}",
    "erz.hinweis": "Hinweis: {0}",
    "kopie.ok": "Modelfile kopiert.",
    "kopie.fehler": "Kopieren nicht möglich – Text markieren und selbst kopieren.",
    "start.fehler": "Endpunkte nicht ladbar: {0}",
  },
  en: {
    "kopf.unter": "The telescope for Ollama: browse models, build a Modelfile, load, create and delete.",
    "kopf.endpunkt": "Endpoint",
    "kopf.endpunktNeu": "＋ Endpoint",
    "kopf.aktualisieren": "Refresh",
    "schalter.sprache": "Switch language: German / English",
    "schalter.hell": "Switch to light theme",
    "schalter.dunkel": "Switch to dark theme",
    "karte.ausklappen": "▸ expand",
    "karte.einklappen": "▾ collapse",
    "modelle.titel": "Models",
    "modelle.aktionen": "Actions",
    "modelle.filter": "filter …",
    "spalte.modell": "Model",
    "spalte.modellTitel": "Sort alphabetically",
    "spalte.groesse": "Size",
    "spalte.groesseTitel": "Sort by size",
    "spalte.familie": "Family",
    "spalte.familieTitel": "Sort by family",
    "spalte.parameter": "Parameters",
    "spalte.parameterTitel": "Sort by parameter count",
    "spalte.quant": "Quant",
    "spalte.quantTitel": "Sort by quantisation",
    "spalte.geaendert": "changed",
    "spalte.geaendertTitel": "Sort by modification date",
    "modelfile.titel": "Modelfile",
    "modelfile.ausrollen": "⇄ Roll out",
    "modelfile.loeschen": "🗑 Delete",
    "modelfile.kopieren": "Copy",
    "modelfile.datei": "Save as file",
    "modelfile.hinweisLeer": "Click “Modelfile” on a model to edit it here.",
    "modelfile.platzhalter": 'FROM qwen3.5:9b\nPARAMETER num_ctx 32768\nSYSTEM """You are …"""',
    "modelfile.neuerName": "New model name",
    "modelfile.namePlatzhalter": "my-model:latest",
    "modelfile.erzeugen": "Create model",
    "modelfile.schreibHinweis": 'This endpoint is read-only. Creating and deleting are locked – set <code>"schreiben": true</code> for the endpoint in <code>config.json</code>.',
    "ep.titel": "Endpoints",
    "ep.hinweis": "Stored in config.json and effective immediately.",
    "ep.neu": "Add a new endpoint",
    "ep.name": "Name",
    "ep.namePlatzhalter": "e.g. workshop",
    "ep.url": "URL",
    "ep.urlPlatzhalter": "http://10.0.0.50:11434",
    "ep.schreiben": "Allow creating and deleting on this endpoint",
    "ep.schliessen": "Close",
    "ep.eintragen": "Add",
    "ep.abbrechen": "Cancel",
    "ep.wegTitel": "Remove endpoint?",
    "ep.wegText": "is removed from the list and from config.json. Models on the endpoint stay untouched.",
    "ep.wegJa": "Yes, remove",
    "ep.ausConf": "from ollamaskope.conf",
    "ep.entfernen": "Remove",
    "ep.nurLesen": " · read only",
    "ep.hinweisConf": "Endpoints from ollamaskope.conf are fixed – edit them there. New ones go to config.json.",
    "ep.nameUrlFehlt": "Please give a name and a URL.",
    "ep.eingetragen": "{0} added (Ollama {1}).",
    "ep.entfernt": "Endpoint removed.",
    "abh.titel": "Dependencies",
    "abh.status": "checking the Modelfiles …",
    "abh.loeschen": "Delete this model",
    "abh.schliessen": "Close",
    "abh.pruefe": "checking the Modelfiles of all models …",
    "abh.bautAuf": "built on",
    "abh.darauf": "built upon by",
    "abh.geschwister": "Siblings (same base)",
    "abh.keinElternteil": "No parent recorded.",
    "abh.keinKind": "No other model is built on it.",
    "abh.keine": "None.",
    "abh.ausDatei": 'Built from a file: <code>{0}</code> – no model on this endpoint.',
    "abh.ausRegistry": "Pulled from the registry – no parent recorded.",
    "abh.geprueft": "{0} models checked ({1})",
    "abh.zwischen": "cached",
    "abh.jetzt": "just now",
    "abh.ohneAntwort": " · {0} without answer",
    "abh.nichtLadbar": "Cannot load: {0}",
    "abh.nichtDa": "not on this endpoint",
    "loeschen.titel": "Really delete this model?",
    "loeschen.text1": "The model",
    "loeschen.text2": "is removed from the endpoint together with its files. This cannot be undone.",
    "loeschen.abbrechen": "Cancel",
    "loeschen.ja": "Yes, delete",
    "loeschen.ok": "{0} deleted.",
    "ausroll.titel": "Roll out model",
    "ausroll.von": "from",
    "ausroll.hinweis": "Only the recipe is transferred – base, parameters, template and system text. The weights stay where they are: the base must exist on the target.",
    "ausroll.ziel": "Target endpoint",
    "ausroll.name": "Name on the target",
    "ausroll.basis": "Pull the missing base there (downloads it from the registry, may be several GB)",
    "ausroll.datei": "GGUF path on the target",
    "ausroll.dateiOptional": "(GGUF models only, optional)",
    "ausroll.dateiPlatzhalter": "leave empty if the file has the same name there",
    "ausroll.abbrechen": "Cancel",
    "ausroll.ja": "Roll out",
    "ausroll.keinZiel": "No other endpoint with write access configured.",
    "ausroll.nameFehlt": "Please give a name for the target.",
    "ausroll.laeuft": "Rolling out: {0} from {1} to {2} as {3} …",
    "ausroll.ok": "{0} is now on {1}.",
    "status.laedt": "loading …",
    "status.erreichbar": "reachable · Ollama {0} · {1} models",
    "status.fehler": "not reachable",
    "liste.keinTreffer": "No model matches the filter.",
    "liste.leer": "This endpoint reports no models.",
    "aktion.laden": "Load",
    "aktion.entladen": "Unload",
    "aktion.ladenTitel": "Load into memory (30 minutes)",
    "aktion.entladenTitel": "Remove from memory",
    "aktion.entladenLeer": "Not in memory – nothing to unload",
    "aktion.geladen": "loaded",
    "aktion.abhTitel": "Show dependencies",
    "schreib.hinweis": 'Read only: this endpoint is set to "schreiben": false in config.json – creating and deleting are locked.',
    "titel.loeschen": "Delete model",
    "titel.gesperrt": "Endpoint is read-only (config.json: schreiben=false)",
    "titel.ausrollen": "Rebuild this model on another endpoint",
    "titel.ausrollenKeinZiel": "No other endpoint with write access configured",
    "toast.laedt": "{0} is loading …",
    "toast.entlaedt": "{0} is unloading …",
    "toast.geladen": "{0} is loaded (30 minutes).",
    "toast.entladen": "{0} unloaded.",
    "mf.laedt": "loading Modelfile …",
    "mf.hinweis": "Edit it and create a new model from it. FROM points to a model that exists on the endpoint.",
    "mf.fehler": "Cannot load Modelfile: {0}",
    "erz.gesperrt": "This endpoint is read-only.",
    "erz.nameFehlt": "Please give a model name.",
    "erz.leer": "The Modelfile is empty.",
    "erz.laeuft": "Creating {0} on {1} …",
    "erz.fertig": "done",
    "erz.ok": "Model {0} created.",
    "erz.ohneErfolg": "Finished without a success message – check the log.",
    "erz.fehler": "Error: {0}",
    "erz.hinweis": "Note: {0}",
    "kopie.ok": "Modelfile copied.",
    "kopie.fehler": "Copying failed – select the text and copy it yourself.",
    "start.fehler": "Cannot load endpoints: {0}",
  },
};

let sprache = "de";

function t(schluessel, ...werte) {
  const tabelle = TEXTE[sprache] || TEXTE.de;
  const text = tabelle[schluessel] ?? TEXTE.de[schluessel] ?? schluessel;
  if (!werte.length) return text;
  return text.replace(/\{(\d+)\}/g, (treffer, nummer) => werte[nummer] ?? treffer);
}

function spracheLaden() {
  const gespeichert = localStorage.getItem("ollamaskope-sprache");
  if (gespeichert === "de" || gespeichert === "en") {
    sprache = gespeichert;
    return;
  }
  sprache = (navigator.language || "de").toLowerCase().startsWith("de") ? "de" : "en";
}

function spracheAnwenden() {
  document.documentElement.lang = sprache;
  for (const knoten of document.querySelectorAll("[data-i18n]")) {
    knoten.textContent = t(knoten.dataset.i18n);
  }
  for (const knoten of document.querySelectorAll("[data-i18n-html]")) {
    knoten.innerHTML = t(knoten.dataset.i18nHtml);
  }
  for (const knoten of document.querySelectorAll("[data-i18n-placeholder]")) {
    knoten.setAttribute("placeholder", t(knoten.dataset.i18nPlaceholder));
  }
  for (const knoten of document.querySelectorAll("[data-i18n-title]")) {
    if (knoten.id !== "thema") knoten.setAttribute("title", t(knoten.dataset.i18nTitle));
  }
  for (const knoten of document.querySelectorAll("details.karte > summary")) {
    knoten.dataset.hinweis = t("karte.ausklappen");
    knoten.dataset.hinweisOffen = t("karte.einklappen");
  }
  const sprachKnopf = $("sprache");
  if (sprachKnopf) {
    sprachKnopf.textContent = sprache === "de" ? "EN" : "DE";
    sprachKnopf.title = t("schalter.sprache");
    sprachKnopf.setAttribute("aria-label", sprachKnopf.title);
  }
  themaAnwenden();
  $("modelfile-hinweis").textContent = zustand.modelfileModell
    ? t("mf.hinweis")
    : t("modelfile.hinweisLeer");
  if (zustand.endpunkte.length) {
    zeichnen();
    schreibrechteAnwenden();
  }
  const dialog = $("endpunkt-dialog");
  if (dialog && dialog.open) epListeZeichnen();
}

function spracheUmschalten() {
  sprache = sprache === "de" ? "en" : "de";
  localStorage.setItem("ollamaskope-sprache", sprache);
  spracheAnwenden();
}

function themaLaden() {
  const gespeichert = localStorage.getItem("ollamaskope-thema");
  let thema = gespeichert;
  if (thema !== "hell" && thema !== "dunkel") {
    const hell =
      window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
    thema = hell ? "hell" : "dunkel";
  }
  document.documentElement.dataset.theme = thema;
  themaAnwenden();
}

function themaAnwenden() {
  const dunkel = document.documentElement.dataset.theme !== "hell";
  const knopf = $("thema");
  if (!knopf) return;
  knopf.textContent = dunkel ? "☀" : "☾";
  knopf.title = t(dunkel ? "schalter.hell" : "schalter.dunkel");
  knopf.setAttribute("aria-label", knopf.title);
}

function themaUmschalten() {
  const warHell = document.documentElement.dataset.theme === "hell";
  const thema = warHell ? "dunkel" : "hell";
  document.documentElement.dataset.theme = thema;
  localStorage.setItem("ollamaskope-thema", thema);
  themaAnwenden();
}

const $ = (id) => document.getElementById(id);

const zustand = {
  endpunkte: [],
  endpunkt: null,
  modelle: [],
  geladen: new Set(),
  modelfileModell: null,
  ausrollModell: null,
  loeschModell: null,
  abhModell: null,
  epWeg: null,
  sortierung: { feld: null, richtung: "auf" },
};

function esc(text) {
  return String(text ?? "").replace(/[&<>"']/g, (zeichen) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[zeichen]));
}

function groesse(bytes) {
  if (!bytes) return "–";
  const einheiten = ["B", "KB", "MB", "GB", "TB"];
  let wert = Number(bytes);
  let stufe = 0;
  while (wert >= 1024 && stufe < einheiten.length - 1) {
    wert /= 1024;
    stufe += 1;
  }
  return `${wert.toFixed(stufe > 1 && wert < 10 ? 1 : 0)} ${einheiten[stufe]}`;
}

function datum(iso) {
  if (!iso) return "–";
  const zeit = new Date(iso);
  if (Number.isNaN(zeit.getTime())) return "–";
  const ort = sprache === "de" ? "de-DE" : "en-US";
  return zeit.toLocaleString(ort, { dateStyle: "short", timeStyle: "short" });
}

let toastZeit = null;
function toast(text, art = "ok") {
  const feld = $("toast");
  feld.textContent = text;
  feld.className = `toast ${art}`;
  feld.hidden = false;
  clearTimeout(toastZeit);
  toastZeit = setTimeout(() => { feld.hidden = true; }, 5000);
}

async function anfrage(pfad, optionen = {}) {
  const antwort = await fetch(pfad, {
    ...optionen,
    headers: {
      "X-Anfrage": "ollamaskope",
      "Content-Type": "application/json",
      ...(optionen.headers || {}),
    },
  });
  const text = await antwort.text();
  let daten = {};
  if (text.trim()) {
    try {
      daten = JSON.parse(text);
    } catch {
      daten = { fehler: text.trim() };
    }
  }
  if (!antwort.ok) throw new Error(daten.fehler || `HTTP ${antwort.status}`);
  return daten;
}

function aktuellerEndpunkt() {
  return zustand.endpunkte.find((ep) => ep.id === zustand.endpunkt) || null;
}

function schreibbar() {
  const ep = aktuellerEndpunkt();
  return Boolean(ep && ep.schreiben);
}

async function endpunkteLaden(bevorzugt = null) {
  const daten = await anfrage("/api/endpunkte");
  zustand.endpunkte = daten.endpunkte || [];
  const auswahl = $("endpunkt");
  auswahl.innerHTML = "";
  for (const ep of zustand.endpunkte) {
    const option = document.createElement("option");
    option.value = ep.id;
    option.textContent = ep.name + (ep.schreiben ? "" : t("ep.nurLesen"));
    auswahl.append(option);
  }
  const gemerkt = bevorzugt || localStorage.getItem("ollamaskope-endpunkt");
  zustand.endpunkt = zustand.endpunkte.some((ep) => ep.id === gemerkt)
    ? gemerkt
    : (zustand.endpunkte[0]?.id ?? null);
  auswahl.value = zustand.endpunkt || "";
  if (zustand.endpunkt) localStorage.setItem("ollamaskope-endpunkt", zustand.endpunkt);
}

function epListeZeichnen() {
  const liste = $("endpunkt-liste");
  liste.innerHTML = "";
  let ausDatei = 0;
  for (const ep of zustand.endpunkte) {
    const ausConf = ep.quelle === "conf";
    if (ausConf) ausDatei += 1;
    const punkt = document.createElement("li");
    punkt.className = "ep-eintrag";
    punkt.innerHTML = `
      <span><code>${esc(ep.name)}</code><span class="abh-meta">${esc(ep.url)}</span>${
        ausConf ? `<span class="abh-meta">${esc(t("ep.ausConf"))}</span>` : ""
      }</span>
      ${
        ausConf
          ? ""
          : `<button class="knopf klein gefahr-leise" type="button"
        data-ep-weg="${esc(ep.id)}" data-ep-name="${esc(ep.name)}">${esc(t("ep.entfernen"))}</button>`
      }`;
    liste.append(punkt);
  }
  const hinweis = $("ep-hinweis");
  if (hinweis) {
    hinweis.textContent = ausDatei ? t("ep.hinweisConf") : t("ep.hinweis");
  }
}

function endpunktDialogOeffnen() {
  epListeZeichnen();
  $("ep-fehler").hidden = true;
  $("ep-name").value = "";
  $("ep-url").value = "";
  $("ep-schreiben").checked = false;
  $("endpunkt-dialog").showModal();
  $("ep-name").focus();
}

async function endpunktHinzufuegen() {
  const name = $("ep-name").value.trim();
  const url = $("ep-url").value.trim();
  const schreiben = $("ep-schreiben").checked;
  const fehler = $("ep-fehler");
  fehler.hidden = true;
  if (!name || !url) {
    fehler.textContent = t("ep.nameUrlFehlt");
    fehler.hidden = false;
    return;
  }
  $("ep-hinzufuegen").disabled = true;
  try {
    const daten = await anfrage("/api/endpunkte", {
      method: "POST",
      body: JSON.stringify({ name, url, schreiben }),
    });
    $("endpunkt-dialog").close();
    toast(t("ep.eingetragen", daten.endpunkt.name, daten.version || "?"));
    await endpunkteLaden(daten.endpunkt.id);
    await modelleLaden();
  } catch (ausnahme) {
    fehler.textContent = String(ausnahme.message || ausnahme);
    fehler.hidden = false;
  } finally {
    $("ep-hinzufuegen").disabled = false;
  }
}

function endpunktEntfernenFragen(id, name) {
  zustand.epWeg = id;
  $("ep-weg-name").textContent = name;
  $("ep-weg-fehler").hidden = true;
  $("ep-weg-dialog").showModal();
}

async function endpunktEntfernen() {
  const id = zustand.epWeg;
  if (!id) return;
  $("ep-weg-ja").disabled = true;
  try {
    await anfrage("/api/endpunkte/entfernen", {
      method: "POST",
      body: JSON.stringify({ id }),
    });
    $("ep-weg-dialog").close();
    $("endpunkt-dialog").close();
    toast(t("ep.entfernt"));
    await endpunkteLaden();
    await modelleLaden();
  } catch (ausnahme) {
    const fehler = $("ep-weg-fehler");
    fehler.textContent = String(ausnahme.message || ausnahme);
    fehler.hidden = false;
  } finally {
    $("ep-weg-ja").disabled = false;
  }
}

async function modelleLaden() {
  const ep = aktuellerEndpunkt();
  if (!ep) return;
  const status = $("endpunkt-status");
  status.textContent = t("status.laedt");
  status.className = "status";

  try {
    const daten = await anfrage(`/api/modelle?endpunkt=${encodeURIComponent(ep.id)}`);
    zustand.modelle = daten.modelle || [];
    zustand.geladen = new Set((daten.geladen || []).map((eintrag) => eintrag.name));
    status.textContent = t("status.erreichbar", daten.version || "?", zustand.modelle.length);
    status.className = "status ok";
    $("liste-fehler").hidden = true;
  } catch (fehler) {
    zustand.modelle = [];
    zustand.geladen = new Set();
    status.textContent = t("status.fehler");
    status.className = "status fehler";
    $("liste-fehler").textContent = String(fehler.message || fehler);
    $("liste-fehler").hidden = false;
  }
  zeichnen();
  schreibrechteAnwenden();
}

function sortWert(modell, feld) {
  const details = modell.details || {};
  if (feld === "name") return String(modell.name);
  if (feld === "familie") return String(details.family || "");
  if (feld === "groesse") return Number(modell.size) || 0;
  if (feld === "parameter") {
    const treffer = String(details.parameter_size || "").match(/([\d.]+)\s*([BMK])/i);
    if (!treffer) return Infinity;
    const faktor = { b: 1, m: 1e-3, k: 1e-6 }[treffer[2].toLowerCase()] ?? 1;
    return parseFloat(treffer[1]) * faktor;
  }
  if (feld === "quantisierung") {
    const treffer = String(details.quantization_level || "").match(/(\d+)/);
    return treffer ? Number(treffer[1]) : Infinity;
  }
  if (feld === "geaendert") {
    const zeit = Date.parse(modell.modified_at || "");
    return Number.isNaN(zeit) ? 0 : zeit;
  }
  return 0;
}

function sortieren(liste) {
  const { feld, richtung } = zustand.sortierung;
  if (!feld) return liste;
  const faktor = richtung === "ab" ? -1 : 1;
  const istText = feld === "name" || feld === "familie";
  return [...liste].sort((a, b) => {
    const links = sortWert(a, feld);
    const rechts = sortWert(b, feld);
    if (istText) {
      return faktor * String(links).localeCompare(String(rechts), sprache, {
        numeric: true,
        sensitivity: "base",
      });
    }
    if (links === rechts) return 0;
    return faktor * (links < rechts ? -1 : 1);
  });
}

function pfeileZeichnen() {
  const { feld, richtung } = zustand.sortierung;
  for (const kopf of document.querySelectorAll("th[data-sort]")) {
    if (kopf.dataset.sort === feld) kopf.dataset.richtung = richtung;
    else delete kopf.dataset.richtung;
  }
}

function sortierungUmschalten(feld) {
  const jetzt = zustand.sortierung;
  if (jetzt.feld !== feld) zustand.sortierung = { feld, richtung: "auf" };
  else if (jetzt.richtung === "auf") zustand.sortierung = { feld, richtung: "ab" };
  else zustand.sortierung = { feld: null, richtung: "auf" };
  zeichnen();
}

function zeichnen() {
  const filter = $("filter").value.trim().toLowerCase();
  const sichtbar = sortieren(
    zustand.modelle.filter(
      (modell) => !filter || String(modell.name).toLowerCase().includes(filter),
    ),
  );
  pfeileZeichnen();

  const tbody = $("modelle");
  tbody.innerHTML = "";
  for (const modell of sichtbar) {
    const details = modell.details || {};
    const istGeladen = zustand.geladen.has(modell.name);
    const zeile = document.createElement("tr");
    zeile.innerHTML = `
      <td class="aktionen">
        <button class="knopf klein" type="button" data-aktion="laden"
          data-modell="${esc(modell.name)}"
          title="${esc(t("aktion.ladenTitel"))}">${esc(t("aktion.laden"))}</button>
        <button class="knopf klein" type="button" data-aktion="entladen"
          data-modell="${esc(modell.name)}"${istGeladen ? "" : " disabled"}
          title="${esc(t(istGeladen ? "aktion.entladenTitel" : "aktion.entladenLeer"))}">${esc(t("aktion.entladen"))}</button>
        <button class="knopf klein" type="button" data-aktion="modelfile"
          data-modell="${esc(modell.name)}">Modelfile</button>
      </td>
      <td class="modell"><button class="modell-knopf" type="button"
        data-aktion="abhaengigkeiten" data-modell="${esc(modell.name)}"
        title="${esc(t("aktion.abhTitel"))}">${esc(modell.name)}</button>${
        zustand.geladen.has(modell.name)
          ? `<span class="chip">${esc(t("aktion.geladen"))}</span>`
          : ""
      }</td>
      <td>${groesse(modell.size)}</td>
      <td>${esc(details.family || "–")}</td>
      <td>${esc(details.parameter_size || "–")}</td>
      <td>${esc(details.quantization_level || "–")}</td>
      <td>${datum(modell.modified_at)}</td>`;
    tbody.append(zeile);
  }

  $("anzahl").textContent = zustand.modelle.length
    ? `${sichtbar.length}/${zustand.modelle.length}`
    : "";
  $("leer").hidden = sichtbar.length > 0;
  $("leer").textContent = zustand.modelle.length
    ? t("liste.keinTreffer")
    : t("liste.leer");
  $("modelfile-name").textContent = zustand.modelfileModell || "";
}

function schreibrechteAnwenden() {
  const darf = schreibbar();
  $("erzeugen").disabled = !darf;
  $("schreib-hinweis").hidden = darf;
  const hinweis = $("liste-hinweis");
  hinweis.hidden = darf;
  hinweis.textContent = darf ? "" : t("schreib.hinweis");
  const editorKnopf = $("modell-loeschen");
  editorKnopf.hidden = !zustand.modelfileModell;
  editorKnopf.disabled = !darf;
  editorKnopf.title = darf ? t("titel.loeschen") : t("titel.gesperrt");
  const ausrollKnopf = $("modell-ausrollen");
  const anderesZiel = zustand.endpunkte.some(
    (ep) => ep.id !== zustand.endpunkt && ep.schreiben,
  );
  ausrollKnopf.hidden = !zustand.modelfileModell;
  ausrollKnopf.disabled = !anderesZiel;
  ausrollKnopf.title = anderesZiel ? t("titel.ausrollen") : t("titel.ausrollenKeinZiel");
  const abhKnopf = $("abh-loeschen");
  abhKnopf.disabled = !darf;
  abhKnopf.title = darf ? "" : t("titel.gesperrt");
}

function vorschlagName(modell) {
  const doppelpunkt = modell.lastIndexOf(":");
  if (doppelpunkt > 0) return `${modell.slice(0, doppelpunkt)}-neu${modell.slice(doppelpunkt)}`;
  return `${modell}-neu`;
}

async function modellLadenOderEntladen(modell, laden) {
  const ep = aktuellerEndpunkt();
  if (!ep) return;
  toast(t(laden ? "toast.laedt" : "toast.entlaedt", modell));
  try {
    await anfrage(laden ? "/api/laden" : "/api/entladen", {
      method: "POST",
      body: JSON.stringify({ endpunkt: ep.id, modell }),
    });
    toast(t(laden ? "toast.geladen" : "toast.entladen", modell));
    await modelleLaden();
  } catch (fehler) {
    toast(String(fehler.message || fehler), "fehler");
  }
}

async function modelfileLaden(modell) {
  const ep = aktuellerEndpunkt();
  if (!ep) return;
  $("modelfile-hinweis").textContent = t("mf.laedt");
  try {
    const daten = await anfrage("/api/modelfile", {
      method: "POST",
      body: JSON.stringify({ endpunkt: ep.id, modell }),
    });
    zustand.modelfileModell = modell;
    schreibrechteAnwenden();
    $("modelfile").value = daten.modelfile || "";
    $("modelfile-name").textContent = modell;
    $("modelfile-hinweis").textContent = t("mf.hinweis");
    $("neuer-name").value = vorschlagName(modell);

    const warnungen = $("warnungen");
    warnungen.innerHTML = "";
    for (const warnung of daten.warnungen || []) {
      const punkt = document.createElement("li");
      punkt.textContent = warnung;
      warnungen.append(punkt);
    }
    warnungen.hidden = (daten.warnungen || []).length === 0;
  } catch (fehler) {
    $("modelfile-hinweis").textContent = t("mf.fehler", fehler.message || fehler);
  }
}

function logZeile(text, istFehler = false) {
  const log = $("log");
  const zeile = document.createElement("div");
  zeile.className = istFehler ? "log-zeile fehler" : "log-zeile";
  zeile.textContent = text;
  log.append(zeile);
  log.scrollTop = log.scrollHeight;
}

async function stromZeilen(antwort, verarbeiten) {
  const leser = antwort.body.getReader();
  const dekoder = new TextDecoder();
  let rest = "";
  for (;;) {
    const { value, done } = await leser.read();
    if (done) break;
    rest += dekoder.decode(value, { stream: true });
    const zeilen = rest.split("\n");
    rest = zeilen.pop();
    for (const zeile of zeilen) verarbeiten(zeile);
  }
  verarbeiten(rest);
}

async function erzeugen() {
  const ep = aktuellerEndpunkt();
  if (!ep) return;
  if (!schreibbar()) {
    toast(t("erz.gesperrt"), "fehler");
    return;
  }
  const name = $("neuer-name").value.trim();
  const modelfile = $("modelfile").value;
  if (!name) {
    toast(t("erz.nameFehlt"), "fehler");
    $("neuer-name").focus();
    return;
  }
  if (!modelfile.trim()) {
    toast(t("erz.leer"), "fehler");
    return;
  }

  const log = $("log");
  log.hidden = false;
  log.textContent = "";
  logZeile(t("erz.laeuft", name, ep.name));
  $("erzeugen").disabled = true;

  try {
    const antwort = await fetch("/api/erzeugen", {
      method: "POST",
      headers: { "X-Anfrage": "ollamaskope", "Content-Type": "application/json" },
      body: JSON.stringify({ endpunkt: ep.id, name, modelfile }),
    });
    if (!antwort.ok) {
      const text = await antwort.text();
      let meldung = text;
      try { meldung = JSON.parse(text).fehler || text; } catch { /* Text bleibt */ }
      throw new Error(meldung);
    }

    let erfolg = false;
    let fehlerText = null;

    const verarbeiten = (zeile) => {
      if (!zeile.trim()) return;
      let meldung;
      try {
        meldung = JSON.parse(zeile);
      } catch {
        logZeile(zeile);
        return;
      }
      if (meldung.error) {
        fehlerText = meldung.error;
        logZeile(t("erz.fehler", meldung.error), true);
      } else if (meldung.hinweis) {
        logZeile(t("erz.hinweis", meldung.hinweis));
      } else if (meldung.status === "success") {
        erfolg = true;
        logZeile(t("erz.fertig"));
      } else if (meldung.status) {
        logZeile(meldung.status);
      }
    };

    await stromZeilen(antwort, verarbeiten);

    if (erfolg && !fehlerText) {
      toast(t("erz.ok", name));
      await modelleLaden();
    } else {
      toast(fehlerText || t("erz.ohneErfolg"), "fehler");
    }
  } catch (fehler) {
    logZeile(t("erz.fehler", fehler.message || fehler), true);
    toast(String(fehler.message || fehler), "fehler");
  } finally {
    $("erzeugen").disabled = !schreibbar();
  }
}

function abhZeile(eintrag) {
  const teile = [eintrag.parameter, eintrag.quantisierung, groesse(eintrag.groesse)]
    .filter((teil) => teil && teil !== "–");
  const zusatz = teile.length
    ? `<span class="abh-meta">${esc(teile.join(" · "))}</span>`
    : "";
  if (!eintrag.vorhanden) {
    return `<li><code>${esc(eintrag.modell)}</code><span class="abh-meta">${esc(t("abh.nichtDa"))}</span></li>`;
  }
  return `<li><button class="abh-link" type="button" data-waehlen="${esc(eintrag.modell)}">
    <code>${esc(eintrag.modell)}</code></button>${zusatz}</li>`;
}

function abhGruppe(titel, eintraege, leer) {
  const inhalt = eintraege.length
    ? `<ul class="abh-liste">${eintraege.map(abhZeile).join("")}</ul>`
    : `<p class="abh-leer">${esc(leer)}</p>`;
  return `<section class="abh-gruppe"><h3>${esc(titel)}</h3>${inhalt}</section>`;
}

async function abhaengigkeitenZeigen(modell) {
  const ep = aktuellerEndpunkt();
  if (!ep || !modell) return;
  zustand.abhModell = modell;
  $("abh-modell").textContent = modell;
  $("abh-status").hidden = false;
  $("abh-status").textContent = t("abh.pruefe");
  $("abh-inhalt").innerHTML = "";
  const dialog = $("abh-dialog");
  if (!dialog.open) dialog.showModal();

  try {
    const daten = await anfrage(
      `/api/abhaengigkeiten?endpunkt=${encodeURIComponent(ep.id)}&modell=${encodeURIComponent(modell)}`,
    );
    let basis;
    if (daten.basis === "datei") {
      basis = `<section class="abh-gruppe"><h3>${esc(t("abh.bautAuf"))}</h3><p class="abh-leer">${t("abh.ausDatei", esc(daten.basis_roh))}</p></section>`;
    } else if (daten.basis === "registry") {
      basis = `<section class="abh-gruppe"><h3>${esc(t("abh.bautAuf"))}</h3><p class="abh-leer">${esc(t("abh.ausRegistry"))}</p></section>`;
    } else {
      basis = abhGruppe(t("abh.bautAuf"), daten.baut_auf, t("abh.keinElternteil"));
    }
    $("abh-inhalt").innerHTML =
      basis +
      abhGruppe(t("abh.darauf"), daten.darauf_bauen, t("abh.keinKind")) +
      abhGruppe(t("abh.geschwister"), daten.geschwister, t("abh.keine"));
    zustand.abhModell = daten.modell || modell;
    schreibrechteAnwenden();
    const fehler = (daten.fehler || []).length;
    $("abh-status").textContent =
      t("abh.geprueft", daten.geprueft, daten.aus_speicher ? t("abh.zwischen") : t("abh.jetzt")) +
      (fehler ? t("abh.ohneAntwort", fehler) : "");
  } catch (fehler) {
    $("abh-status").textContent = t("abh.nichtLadbar", fehler.message || fehler);
  }
}

function loeschenOeffnen(modell) {
  if (!modell) return;
  if (!schreibbar()) {
    toast(t("erz.gesperrt"), "fehler");
    return;
  }
  zustand.loeschModell = modell;
  $("loeschen-modell").textContent = modell;
  $("loeschen-ja").disabled = false;
  $("loeschen-fehler").hidden = true;
  $("loeschen-dialog").showModal();
  $("loeschen-ja").focus();
}

async function loeschen() {
  const ep = aktuellerEndpunkt();
  const modell = zustand.loeschModell;
  if (!ep || !modell) return;
  $("loeschen-ja").disabled = true;
  try {
    await anfrage("/api/loeschen", {
      method: "POST",
      body: JSON.stringify({
        endpunkt: ep.id,
        modell,
        bestaetigung: modell,
      }),
    });
    $("loeschen-dialog").close();
    toast(t("loeschen.ok", modell));
    if (zustand.modelfileModell === modell) {
      zustand.modelfileModell = null;
      $("modelfile").value = "";
      $("modelfile-name").textContent = "";
    }
    await modelleLaden();
  } catch (fehler) {
    const feld = $("loeschen-fehler");
    feld.textContent = String(fehler.message || fehler);
    feld.hidden = false;
    $("loeschen-ja").disabled = false;
  }
}

function ausrollOeffnen() {
  const ep = aktuellerEndpunkt();
  const modell = zustand.modelfileModell;
  if (!ep || !modell) return;
  const ziele = zustand.endpunkte.filter((eintrag) => eintrag.id !== ep.id);
  if (!ziele.some((eintrag) => eintrag.schreiben)) {
    toast(t("ausroll.keinZiel"), "fehler");
    return;
  }
  zustand.ausrollModell = modell;
  $("ausroll-modell").textContent = modell;
  $("ausroll-quelle").textContent = ep.name;
  $("ausroll-name").value = modell;
  $("ausroll-fehler").hidden = true;
  $("ausroll-basis").checked = false;
  $("ausroll-datei").value = "";

  const auswahl = $("ausroll-ziel");
  auswahl.innerHTML = "";
  for (const eintrag of ziele) {
    const option = document.createElement("option");
    option.value = eintrag.id;
    option.dataset.name = eintrag.name;
    option.textContent = eintrag.schreiben
      ? eintrag.name
      : `${eintrag.name}${t("ep.nurLesen")}`;
    option.disabled = !eintrag.schreiben;
    auswahl.append(option);
  }
  auswahl.value = ziele.find((eintrag) => eintrag.schreiben).id;
  $("ausroll-dialog").showModal();
  $("ausroll-name").select();
}

async function ausrollen() {
  const ep = aktuellerEndpunkt();
  const modell = zustand.ausrollModell;
  const ziel = $("ausroll-ziel").value;
  const zielName = $("ausroll-ziel").selectedOptions[0]?.dataset.name || ziel;
  const name = $("ausroll-name").value.trim();
  if (!ep || !modell || !ziel) return;
  if (!name) {
    toast(t("ausroll.nameFehlt"), "fehler");
    $("ausroll-name").focus();
    return;
  }

  $("ausroll-dialog").close();
  const log = $("log");
  log.hidden = false;
  log.textContent = "";
  logZeile(t("ausroll.laeuft", modell, ep.name, zielName, name));
  $("modell-ausrollen").disabled = true;

  try {
    const antwort = await fetch("/api/ausrollen", {
      method: "POST",
      headers: { "X-Anfrage": "ollamaskope", "Content-Type": "application/json" },
      body: JSON.stringify({
        quelle: ep.id,
        ziel,
        modell,
        name,
        basis_ziehen: $("ausroll-basis").checked,
        basis_datei: $("ausroll-datei").value.trim(),
      }),
    });
    if (!antwort.ok) {
      const text = await antwort.text();
      let meldung = text;
      try { meldung = JSON.parse(text).fehler || text; } catch { /* Text bleibt */ }
      throw new Error(meldung);
    }

    let erfolg = false;
    let fehlerText = null;
    await stromZeilen(antwort, (zeile) => {
      if (!zeile.trim()) return;
      let meldung;
      try {
        meldung = JSON.parse(zeile);
      } catch {
        logZeile(zeile);
        return;
      }
      if (meldung.error) {
        fehlerText = meldung.error;
        logZeile(t("erz.fehler", meldung.error), true);
      } else if (meldung.hinweis) {
        logZeile(t("erz.hinweis", meldung.hinweis));
      } else if (meldung.status === "success") {
        erfolg = true;
        logZeile(t("erz.fertig"));
      } else if (meldung.status) {
        logZeile(meldung.status);
      }
    });

    if (erfolg && !fehlerText) {
      toast(t("ausroll.ok", name, zielName));
    } else {
      toast(fehlerText || t("erz.ohneErfolg"), "fehler");
    }
  } catch (fehler) {
    logZeile(t("erz.fehler", fehler.message || fehler), true);
    toast(String(fehler.message || fehler), "fehler");
  } finally {
    schreibrechteAnwenden();
  }
}

async function start() {
  themaLaden();
  spracheLaden();
  spracheAnwenden();
  $("sprache").addEventListener("click", spracheUmschalten);
  $("thema").addEventListener("click", themaUmschalten);

  try {
    await endpunkteLaden();
  } catch (fehler) {
    toast(t("start.fehler", fehler.message || fehler), "fehler");
    return;
  }

  $("endpunkt").addEventListener("change", async (ereignis) => {
    zustand.endpunkt = ereignis.target.value;
    zustand.modelfileModell = null;
    $("modelfile").value = "";
    $("modelfile-name").textContent = "";
    $("warnungen").hidden = true;
    $("log").hidden = true;
    localStorage.setItem("ollamaskope-endpunkt", zustand.endpunkt);
    await modelleLaden();
  });
  $("aktualisieren").addEventListener("click", () => modelleLaden());
  $("endpunkte-verwalten").addEventListener("click", endpunktDialogOeffnen);
  $("ep-schliessen").addEventListener("click", () => $("endpunkt-dialog").close());
  $("ep-hinzufuegen").addEventListener("click", endpunktHinzufuegen);
  $("endpunkt-liste").addEventListener("click", (ereignis) => {
    const knopf = ereignis.target.closest("button[data-ep-weg]");
    if (knopf) endpunktEntfernenFragen(knopf.dataset.epWeg, knopf.dataset.epName);
  });
  $("ep-weg-abbrechen").addEventListener("click", () => $("ep-weg-dialog").close());
  $("ep-weg-ja").addEventListener("click", endpunktEntfernen);
  $("filter").addEventListener("input", zeichnen);
  for (const kopf of document.querySelectorAll("th[data-sort] button")) {
    kopf.addEventListener("click", () => sortierungUmschalten(kopf.dataset.sort));
  }
  $("erzeugen").addEventListener("click", erzeugen);
  $("modell-loeschen").addEventListener("click", () => {
    if (zustand.modelfileModell) loeschenOeffnen(zustand.modelfileModell);
  });
  $("modell-ausrollen").addEventListener("click", ausrollOeffnen);
  $("ausroll-abbrechen").addEventListener("click", () => $("ausroll-dialog").close());
  $("ausroll-ja").addEventListener("click", ausrollen);
  $("modelle").addEventListener("click", (ereignis) => {
    const knopf = ereignis.target.closest("button[data-aktion]");
    if (!knopf) return;
    if (knopf.dataset.aktion === "modelfile") modelfileLaden(knopf.dataset.modell);
    if (knopf.dataset.aktion === "loeschen") loeschenOeffnen(knopf.dataset.modell);
    if (knopf.dataset.aktion === "abhaengigkeiten") abhaengigkeitenZeigen(knopf.dataset.modell);
    if (knopf.dataset.aktion === "laden") modellLadenOderEntladen(knopf.dataset.modell, true);
    if (knopf.dataset.aktion === "entladen") modellLadenOderEntladen(knopf.dataset.modell, false);
  });

  $("abh-inhalt").addEventListener("click", (ereignis) => {
    const knopf = ereignis.target.closest("button[data-waehlen]");
    if (!knopf) return;
    modelfileLaden(knopf.dataset.waehlen);
    abhaengigkeitenZeigen(knopf.dataset.waehlen);
  });
  $("abh-schliessen").addEventListener("click", () => $("abh-dialog").close());
  $("abh-loeschen").addEventListener("click", () => {
    const modell = zustand.abhModell;
    if (!modell) return;
    $("abh-dialog").close();
    loeschenOeffnen(modell);
  });

  $("kopieren").addEventListener("click", async () => {
    const text = $("modelfile").value;
    if (!text.trim()) return;
    try {
      await navigator.clipboard.writeText(text);
      toast(t("kopie.ok"));
    } catch {
      toast(t("kopie.fehler"), "fehler");
    }
  });
  $("herunterladen").addEventListener("click", () => {
    const text = $("modelfile").value;
    if (!text.trim()) return;
    const blob = new Blob([text], { type: "text/plain" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "Modelfile";
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 2000);
  });

  $("loeschen-ja").addEventListener("click", loeschen);
  $("loeschen-abbrechen").addEventListener("click", () => $("loeschen-dialog").close());

  await modelleLaden();
}

start();
