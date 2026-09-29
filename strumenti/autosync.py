#!/usr/bin/env python3
"""Sincronizzazione automatica del libro (gira in background).

Ogni minuto:
  - i .docx di word/ modificati, chiusi e fermi da almeno 30 secondi
    vengono salvati in Git (sincronizza.py salva);
  - ogni 5 minuti si scaricano le novita' dall'altro PC e si rigenerano
    i .docx dei capitoli arrivati, se non sono aperti e non hanno modifiche.

Un .docx aperto in LibreOffice o Word non viene mai toccato.
Conflitti ed errori ripetuti vengono segnalati con una notifica sul desktop.
Registro: word/.stato/autosync.log

Funziona su Linux e su Windows (le notifiche su Windows richiedono il modulo
PowerShell BurntToast: `Install-Module BurntToast -Scope CurrentUser`).

Uso:  python3 autosync.py            (ciclo continuo)
      python3 autosync.py --una-volta (un solo giro, per prova)
"""
import datetime
import glob
import json
import os
import subprocess
import sys
import time

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
WORD = os.path.join(RADICE, "word")
CAPITOLI = os.path.join(RADICE, "capitoli")
SYNC = os.path.join(QUI, "sincronizza.py")
LOG = os.path.join(WORD, ".stato", "autosync.log")

GIRO = 60            # secondi tra un controllo e l'altro
QUIETE = 30          # secondi senza modifiche prima di salvare
SCARICA_OGNI = 5     # giri tra un controllo dell'altro PC e l'altro

sys.path.insert(0, QUI)
import sincronizza as sz  # noqa: E402


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    riga = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(riga, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(riga + "\n")


def notifica(titolo, testo, urgente=False):
    """Notifica sul desktop: notify-send su Linux, BurntToast su Windows (se installato)."""
    try:
        if os.name == "nt":
            ps = ("if (Get-Module -ListAvailable -Name BurntToast) { Import-Module BurntToast; "
                  "New-BurntToastNotification -Text %s, %s }"
                  % (json.dumps(titolo), json.dumps(testo)))
            subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                           timeout=20, creationflags=sz.SENZA_FINESTRA)
        else:
            subprocess.run(["notify-send", "-a", "Libro", "-u", "critical" if urgente else "normal",
                            titolo, testo], timeout=10)
    except Exception:
        pass


def aperto(nome):
    """True se il .docx e' aperto in LibreOffice o Word."""
    if os.path.exists(os.path.join(WORD, f".~lock.{nome}.docx#")):
        return True
    return os.path.exists(os.path.join(WORD, "~$" + nome[2:] + ".docx"))


def esegui(*args):
    r = subprocess.run([sys.executable, SYNC, *args], capture_output=True, text=True, cwd=RADICE,
                       creationflags=sz.SENZA_FINESTRA)
    out = (r.stdout + r.stderr).strip()
    dati = {}
    for riga in r.stdout.splitlines():
        if riga.startswith("{"):
            try:
                dati = json.loads(riga)
            except ValueError:
                pass
    return r.returncode, dati, out


class Stato:
    def __init__(self):
        self.giro = 0
        self.bloccati = {}       # capitolo -> sha del docx che ha dato conflitto
        self.errori_rete = 0


def salva_modificati(st):
    stato = sz.carica_stato()
    for nome in sz.docx_modificati(stato):
        path = os.path.join(WORD, nome + ".docx")
        if aperto(nome) or time.time() - os.path.getmtime(path) < QUIETE:
            continue
        firma = sz.sha(path)
        if st.bloccati.get(nome) == firma:
            continue  # conflitto gia' segnalato: si riprova solo dopo una nuova modifica
        rc, dati, out = esegui("salva", nome, "-m", f"{nome}: salvataggio automatico")
        if rc == 0:
            st.bloccati.pop(nome, None)
            st.errori_rete = 0
            if not dati.get("commit"):
                continue  # il .docx e' cambiato ma il testo no (es. solo formattazione)
            uniti = " (unito con le modifiche dell'altro PC: riapri il file)" if dati.get("uniti_con_altro_pc") else ""
            log(f"salvato {nome}{uniti}")
            notifica("Capitolo salvato", nome + uniti)
        elif rc == 3 and dati.get("conflitti"):
            st.bloccati[nome] = firma
            log(f"CONFLITTO {nome}: {out}")
            notifica("Conflitto nel capitolo " + nome,
                     "Lo stesso passaggio e' stato cambiato sui due PC. Chiedi a Claude di risolverlo.",
                     urgente=True)
        else:
            gestisci_errore(st, f"salva {nome}", out)


def scarica_novita(st):
    if not sz.ha_remoto():
        return
    r = sz.git("fetch", "--quiet", check=False)
    if r.returncode != 0:
        gestisci_errore(st, "fetch", r.stderr)
        return
    st.errori_rete = 0
    dietro = sz.git("rev-list", "--count", "HEAD..@{u}", check=False).stdout.strip()
    stato = sz.carica_stato()
    sporchi = set(sz.docx_modificati(stato))
    # capitoli da aggiornare: arrivati dall'altro PC o senza .docx
    nomi = []
    for md in sorted(glob.glob(os.path.join(CAPITOLI, "*.md"))):
        n = os.path.splitext(os.path.basename(md))[0]
        if n not in sporchi and not aperto(n):
            nomi.append(n)
    if dietro in ("", "0") and all(
            stato.get(n, {}).get("md") == sz.sha(os.path.join(CAPITOLI, n + ".md"))
            and os.path.exists(os.path.join(WORD, n + ".docx")) for n in nomi):
        return
    if not nomi:
        return
    rc, dati, out = esegui("apri", *nomi)
    if rc == 0:
        if dati.get("docx_aggiornati"):
            log("aggiornati dall'altro PC: " + ", ".join(dati["docx_aggiornati"]))
            notifica("Capitoli aggiornati", ", ".join(dati["docx_aggiornati"]))
        # capitoli nuovi arrivati: non erano nell'elenco prima del pull
        nuovi = [os.path.splitext(os.path.basename(m))[0]
                 for m in glob.glob(os.path.join(CAPITOLI, "*.md"))
                 if not os.path.exists(os.path.join(WORD, os.path.basename(m)[:-3] + ".docx"))]
        if nuovi:
            rc2, dati2, _ = esegui("apri", *nuovi)
            if rc2 == 0 and dati2.get("docx_aggiornati"):
                log("nuovi capitoli: " + ", ".join(dati2["docx_aggiornati"]))
                notifica("Nuovi capitoli", ", ".join(dati2["docx_aggiornati"]))
    else:
        gestisci_errore(st, "apri", out)


def gestisci_errore(st, cosa, out):
    st.errori_rete += 1
    log(f"errore {cosa}: {out}")
    if st.errori_rete == 10:  # circa 10 minuti di errori consecutivi
        notifica("Libro: sincronizzazione ferma",
                 "Da alcuni minuti non riesco a salvare o scaricare. Controlla la connessione "
                 "o chiedi a Claude di guardare il registro.", urgente=True)


def giro(st):
    try:
        salva_modificati(st)
        if st.giro % SCARICA_OGNI == 0:
            scarica_novita(st)
    except SystemExit as e:  # sincronizza.py usa sys.exit per gli errori
        gestisci_errore(st, "interno", str(e))
    except Exception as e:
        gestisci_errore(st, "imprevisto", repr(e))
    st.giro += 1


def main():
    st = Stato()
    if "--una-volta" in sys.argv:
        giro(st)
        return
    log("avviato")
    while True:
        giro(st)
        time.sleep(GIRO)


if __name__ == "__main__":
    main()
