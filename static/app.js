"use strict";

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
  return zeit.toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" });
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
    option.textContent = ep.name + (ep.schreiben ? "" : " · nur lesen");
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
        ausConf ? '<span class="abh-meta">aus ollamaskope.conf</span>' : ""
      }</span>
      ${
        ausConf
          ? ""
          : `<button class="knopf klein gefahr-leise" type="button"
        data-ep-weg="${esc(ep.id)}" data-ep-name="${esc(ep.name)}">Entfernen</button>`
      }`;
    liste.append(punkt);
  }
  const hinweis = $("ep-hinweis");
  if (hinweis) {
    hinweis.textContent = ausDatei
      ? "Endpunkte aus ollamaskope.conf stehen fest – dort bearbeiten. Neue landen in config.json."
      : "Wird in config.json gespeichert und gilt sofort.";
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
    fehler.textContent = "Name und URL angeben.";
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
    toast(`${daten.endpunkt.name} eingetragen (Ollama ${daten.version || "?"}).`);
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
    toast("Endpunkt entfernt.");
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
  status.textContent = "lädt …";
  status.className = "status";

  try {
    const daten = await anfrage(`/api/modelle?endpunkt=${encodeURIComponent(ep.id)}`);
    zustand.modelle = daten.modelle || [];
    zustand.geladen = new Set((daten.geladen || []).map((eintrag) => eintrag.name));
    status.textContent =
      `erreichbar · Ollama ${daten.version || "?"} · ${zustand.modelle.length} Modelle`;
    status.className = "status ok";
    $("liste-fehler").hidden = true;
  } catch (fehler) {
    zustand.modelle = [];
    zustand.geladen = new Set();
    status.textContent = "nicht erreichbar";
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
      return faktor * String(links).localeCompare(String(rechts), "de", {
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
        <button class="knopf klein" type="button" data-aktion="${istGeladen ? "entladen" : "laden"}"
          data-modell="${esc(modell.name)}"
          title="${istGeladen ? "Aus dem Speicher nehmen" : "In den Speicher laden (30 Minuten)"}">${istGeladen ? "Entladen" : "Laden"}</button>
        <button class="knopf klein" type="button" data-aktion="modelfile"
          data-modell="${esc(modell.name)}">Modelfile</button>
      </td>
      <td class="modell"><button class="modell-knopf" type="button"
        data-aktion="abhaengigkeiten" data-modell="${esc(modell.name)}"
        title="Abhängigkeiten anzeigen">${esc(modell.name)}</button>${
        zustand.geladen.has(modell.name) ? '<span class="chip">geladen</span>' : ""
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
    ? "Kein Modell passt zum Filter."
    : "Dieser Endpunkt meldet keine Modelle.";
  $("modelfile-name").textContent = zustand.modelfileModell || "";
}

function schreibrechteAnwenden() {
  const darf = schreibbar();
  $("erzeugen").disabled = !darf;
  $("schreib-hinweis").hidden = darf;
  const hinweis = $("liste-hinweis");
  hinweis.hidden = darf;
  hinweis.textContent = darf
    ? ""
    : "Nur lesen: dieser Endpunkt steht in config.json auf \"schreiben\": false – Erzeugen und Löschen sind gesperrt.";
  const editorKnopf = $("modell-loeschen");
  editorKnopf.hidden = !zustand.modelfileModell;
  editorKnopf.disabled = !darf;
  editorKnopf.title = darf
    ? "Modell löschen"
    : "Endpunkt ist schreibgeschützt (config.json: schreiben=false)";
  const ausrollKnopf = $("modell-ausrollen");
  const anderesZiel = zustand.endpunkte.some(
    (ep) => ep.id !== zustand.endpunkt && ep.schreiben,
  );
  ausrollKnopf.hidden = !zustand.modelfileModell;
  ausrollKnopf.disabled = !anderesZiel;
  ausrollKnopf.title = anderesZiel
    ? "Dieses Modell auf einem anderen Endpunkt nachbauen"
    : "Kein anderer Endpunkt mit Schreibrecht eingetragen";
  const abhKnopf = $("abh-loeschen");
  abhKnopf.disabled = !darf;
  abhKnopf.title = darf ? "" : "Endpunkt ist schreibgeschützt (config.json: schreiben=false)";
}

function vorschlagName(modell) {
  const doppelpunkt = modell.lastIndexOf(":");
  if (doppelpunkt > 0) return `${modell.slice(0, doppelpunkt)}-neu${modell.slice(doppelpunkt)}`;
  return `${modell}-neu`;
}

async function modellLadenOderEntladen(modell, laden) {
  const ep = aktuellerEndpunkt();
  if (!ep) return;
  toast(laden ? `${modell} wird geladen …` : `${modell} wird entladen …`);
  try {
    await anfrage(laden ? "/api/laden" : "/api/entladen", {
      method: "POST",
      body: JSON.stringify({ endpunkt: ep.id, modell }),
    });
    toast(laden ? `${modell} ist geladen (30 Minuten).` : `${modell} entladen.`);
    await modelleLaden();
  } catch (fehler) {
    toast(String(fehler.message || fehler), "fehler");
  }
}

async function modelfileLaden(modell) {
  const ep = aktuellerEndpunkt();
  if (!ep) return;
  $("modelfile-hinweis").textContent = "lade Modelfile …";
  try {
    const daten = await anfrage("/api/modelfile", {
      method: "POST",
      body: JSON.stringify({ endpunkt: ep.id, modell }),
    });
    zustand.modelfileModell = modell;
    schreibrechteAnwenden();
    $("modelfile-karte").open = true;
    $("modelfile").value = daten.modelfile || "";
    $("modelfile-name").textContent = modell;
    $("modelfile-hinweis").textContent =
      "Bearbeiten und mit neuem Namen erzeugen. FROM zeigt auf ein Modell, das auf dem Endpunkt liegt.";
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
    $("modelfile-hinweis").textContent =
      `Modelfile nicht ladbar: ${fehler.message || fehler}`;
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
    toast("Dieser Endpunkt ist schreibgeschützt.", "fehler");
    return;
  }
  const name = $("neuer-name").value.trim();
  const modelfile = $("modelfile").value;
  if (!name) {
    toast("Bitte einen Modellnamen angeben.", "fehler");
    $("neuer-name").focus();
    return;
  }
  if (!modelfile.trim()) {
    toast("Das Modelfile ist leer.", "fehler");
    return;
  }

  const log = $("log");
  log.hidden = false;
  log.textContent = "";
  logZeile(`Erzeuge ${name} auf ${ep.name} …`);
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
        logZeile(`Fehler: ${meldung.error}`, true);
      } else if (meldung.hinweis) {
        logZeile(`Hinweis: ${meldung.hinweis}`);
      } else if (meldung.status === "success") {
        erfolg = true;
        logZeile("fertig");
      } else if (meldung.status) {
        logZeile(meldung.status);
      }
    };

    await stromZeilen(antwort, verarbeiten);

    if (erfolg && !fehlerText) {
      toast(`Modell ${name} erzeugt.`);
      await modelleLaden();
    } else {
      toast(fehlerText || "Ohne Erfolgsmeldung beendet – Log prüfen.", "fehler");
    }
  } catch (fehler) {
    logZeile(`Fehler: ${fehler.message || fehler}`, true);
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
    return `<li><code>${esc(eintrag.modell)}</code><span class="abh-meta">nicht auf diesem Endpunkt</span></li>`;
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
  $("abh-status").textContent = "prüfe die Modelfiles aller Modelle …";
  $("abh-inhalt").innerHTML = "";
  const dialog = $("abh-dialog");
  if (!dialog.open) dialog.showModal();

  try {
    const daten = await anfrage(
      `/api/abhaengigkeiten?endpunkt=${encodeURIComponent(ep.id)}&modell=${encodeURIComponent(modell)}`,
    );
    let basis;
    if (daten.basis === "datei") {
      basis = `<section class="abh-gruppe"><h3>baut auf</h3><p class="abh-leer">Gebaut aus einer Datei: <code>${esc(daten.basis_roh)}</code> – kein Modell auf diesem Endpunkt.</p></section>`;
    } else if (daten.basis === "registry") {
      basis = `<section class="abh-gruppe"><h3>baut auf</h3><p class="abh-leer">Aus der Registry geladen – kein Elternteil eingetragen.</p></section>`;
    } else {
      basis = abhGruppe("baut auf", daten.baut_auf, "Kein Elternteil eingetragen.");
    }
    $("abh-inhalt").innerHTML =
      basis +
      abhGruppe("darauf bauen auf", daten.darauf_bauen, "Kein anderes Modell baut darauf auf.") +
      abhGruppe("Geschwister (gleiche Basis)", daten.geschwister, "Keine.");
    zustand.abhModell = daten.modell || modell;
    schreibrechteAnwenden();
    const fehler = (daten.fehler || []).length;
    $("abh-status").textContent =
      `${daten.geprueft} Modelle geprüft (${daten.aus_speicher ? "zwischengespeichert" : "gerade eben"})` +
      (fehler ? ` · ${fehler} ohne Antwort` : "");
  } catch (fehler) {
    $("abh-status").textContent = `Nicht ladbar: ${fehler.message || fehler}`;
  }
}

function loeschenOeffnen(modell) {
  if (!modell) return;
  if (!schreibbar()) {
    toast("Dieser Endpunkt ist schreibgeschützt.", "fehler");
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
    toast(`${modell} gelöscht.`);
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
    toast("Kein anderer Endpunkt mit Schreibrecht eingetragen.", "fehler");
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
    option.textContent = eintrag.schreiben ? eintrag.name : `${eintrag.name} (nur lesen)`;
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
    toast("Bitte einen Namen für das Ziel angeben.", "fehler");
    $("ausroll-name").focus();
    return;
  }

  $("ausroll-dialog").close();
  const log = $("log");
  log.hidden = false;
  log.textContent = "";
  logZeile(`Ausrollen: ${modell} von ${ep.name} nach ${zielName} als ${name} …`);
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
        logZeile(`Fehler: ${meldung.error}`, true);
      } else if (meldung.hinweis) {
        logZeile(`Hinweis: ${meldung.hinweis}`);
      } else if (meldung.status === "success") {
        erfolg = true;
        logZeile("fertig");
      } else if (meldung.status) {
        logZeile(meldung.status);
      }
    });

    if (erfolg && !fehlerText) {
      toast(`${name} liegt jetzt auf ${zielName}.`);
    } else {
      toast(fehlerText || "Ohne Erfolgsmeldung beendet – Log prüfen.", "fehler");
    }
  } catch (fehler) {
    logZeile(`Fehler: ${fehler.message || fehler}`, true);
    toast(String(fehler.message || fehler), "fehler");
  } finally {
    schreibrechteAnwenden();
  }
}

async function start() {
  try {
    await endpunkteLaden();
  } catch (fehler) {
    toast(`Endpunkte nicht ladbar: ${fehler.message || fehler}`, "fehler");
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
      toast("Modelfile kopiert.");
    } catch {
      toast("Kopieren nicht möglich – Text markieren und selbst kopieren.", "fehler");
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
