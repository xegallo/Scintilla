#!/usr/bin/env python3
"""Sincronizza i capitoli Word (cartella word/) con i Markdown in Git (capitoli/).

  python strumenti/sincronizza.py elenco                 stato di tutti i capitoli
  python strumenti/sincronizza.py apri 03               scarica da Git e rigenera word/03-....docx
  python strumenti/sincronizza.py salva 03 -m "..."     word/03-....docx -> .md, commit e push
  python strumenti/sincronizza.py risolto 03 -m "..."   dopo aver risolto word/.stato/conflitti/03-....md
  python strumenti/sincronizza.py versione elenco        versioni disponibili e quella in uso
  python strumenti/sincronizza.py versione nuova 12      crea la versione 12 (ramo versione-12)
  python strumenti/sincronizza.py versione passa 12      passa alla versione 12
  python strumenti/sincronizza.py versione passa main    torna alla versione completa
  python strumenti/sincronizza.py versione unisci 12     porta la versione 12 dentro main
  python strumenti/sincronizza.py libro                 esporta/libro.docx con tutti i capitoli
  python strumenti/sincronizza.py libro 00 01 --nome prova   solo alcuni capitoli

Il capitolo si indica con il numero (03), il nome (la-cripta) o il nome completo.

Il Markdown in Git e' la versione di riferimento; i .docx in word/ sono copie di
lavoro (escluse da Git). Per ogni capitolo si ricorda in word/.stato/ la versione
del .md da cui e' nato il .docx: se nel frattempo il capitolo e' cambiato anche
sull'altro PC, le due versioni vengono unite riga per riga (git merge-file).

Codici di uscita: 0 ok, 2 ci sono .docx da salvare prima, 3 conflitto da risolvere,
1 altri errori.
"""
import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
sys.path.insert(0, QUI)
import esporta as esp  # noqa: E402

SENZA_FINESTRA = esp.SENZA_FINESTRA   # niente finestre nere su Windows

CAPITOLI = os.path.join(RADICE, "capitoli")
WORD = os.path.join(RADICE, "word")
STATO_DIR = os.path.join(WORD, ".stato")
STATO = os.path.join(STATO_DIR, "stato.json")
CONFLITTI = os.path.join(STATO_DIR, "conflitti")


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def git(*args, check=True):
    r = subprocess.run(["git", "-C", RADICE, *args], capture_output=True, text=True,
                       creationflags=SENZA_FINESTRA)
    if check and r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        sys.exit(1)
    return r


def ha_remoto():
    return bool(git("remote").stdout.strip())


def pull():
    if ha_remoto():
        r = git("pull", "--no-rebase", "--no-edit", check=False)
        if r.returncode != 0:
            sys.stderr.write(r.stdout + r.stderr)
            print("ERRORE: git pull non riuscito (connessione o conflitto in Git).")
            sys.exit(3)


def carica_stato():
    try:
        with open(STATO, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def salva_stato(stato):
    os.makedirs(STATO_DIR, exist_ok=True)
    with open(STATO, "w", encoding="utf-8") as f:
        json.dump(stato, f, indent=1, ensure_ascii=False)


def base_path(nome):
    return os.path.join(STATO_DIR, nome + ".md")


def docx_modificati(stato):
    out = []
    for d in sorted(glob.glob(os.path.join(WORD, "*.docx"))):
        nome = os.path.splitext(os.path.basename(d))[0]
        if nome.startswith("~$"):  # file temporanei di Word
            continue
        if stato.get(nome, {}).get("docx") != sha(d):
            out.append(nome)
    return out


def rigenera(nome, stato):
    md = os.path.join(CAPITOLI, nome + ".md")
    out = os.path.join(WORD, nome + ".docx")
    try:
        esp.esporta([md], out)
    except PermissionError:
        print(f"ERRORE: {nome}.docx e' aperto in Word. Chiudilo e riprova.")
        sys.exit(1)
    os.makedirs(STATO_DIR, exist_ok=True)
    shutil.copyfile(md, base_path(nome))
    stato[nome] = {"docx": sha(out), "md": sha(md)}


def aggiorna_docx(stato, nomi):
    """Rigenera i .docx indicati se il loro .md non corrisponde piu'
    (mai quelli con modifiche non salvate)."""
    cambiati = []
    sporchi = set(docx_modificati(stato))
    for nome in nomi:
        md = os.path.join(CAPITOLI, nome + ".md")
        if not os.path.exists(md) or nome in sporchi:
            continue
        docx = os.path.join(WORD, nome + ".docx")
        if stato.get(nome, {}).get("md") != sha(md) or not os.path.exists(docx):
            rigenera(nome, stato)
            cambiati.append(nome)
    return cambiati


def tutti_i_nomi():
    nomi = {os.path.splitext(os.path.basename(f))[0]
            for f in glob.glob(os.path.join(CAPITOLI, "*.md")) + glob.glob(os.path.join(WORD, "*.docx"))}
    return sorted(n for n in nomi if not n.startswith("~$"))


def scegli(richiesti):
    """Nomi completi dei capitoli richiesti ('03', 'prologo', '00-prologo')."""
    if not richiesti:
        print("ERRORE: indica il capitolo (es. 00-prologo). Disponibili:", ", ".join(tutti_i_nomi()))
        sys.exit(1)
    scelti = []
    for r in richiesti:
        r = os.path.splitext(os.path.basename(r))[0].lower()
        if r.isdigit():
            r = r.zfill(2)
        esatti = [n for n in tutti_i_nomi() if n.lower() == r]
        trovati = esatti or [n for n in tutti_i_nomi()
                   if n.lower().startswith(r + "-") or r in n.lower().split("-", 1)[-1]]
        if len(trovati) != 1:
            print(f"ERRORE: '{r}' corrisponde a {trovati or 'nessun capitolo'}. "
                  f"Disponibili: {', '.join(tutti_i_nomi())}")
            sys.exit(1)
        scelti.append(trovati[0])
    return scelti


def cmd_elenco(_):
    stato = carica_stato()
    sporchi = set(docx_modificati(stato))
    out = []
    for n in tutti_i_nomi():
        md = os.path.join(CAPITOLI, n + ".md")
        dx = os.path.join(WORD, n + ".docx")
        out.append({
            "capitolo": n,
            "in_git": os.path.exists(md),
            "docx_presente": os.path.exists(dx),
            "docx_da_salvare": n in sporchi,
            "docx_non_aggiornato": os.path.exists(md) and os.path.exists(dx)
            and n not in sporchi and stato.get(n, {}).get("md") != sha(md),
        })
    print(json.dumps({"versione": ramo_corrente(), "capitoli": out}, ensure_ascii=False, indent=1))


def cmd_stato(_):
    mod = docx_modificati(carica_stato())
    print(json.dumps({"docx_da_salvare": mod}, ensure_ascii=False))


def cmd_apri(a):
    stato = carica_stato()
    pull()  # tocca solo capitoli/: i .docx non vengono modificati qui
    nomi = scegli(a.capitoli)
    mod = [n for n in docx_modificati(stato) if n in nomi]
    if mod:
        print("ATTENZIONE: questi .docx hanno modifiche non salvate:", ", ".join(mod))
        print("Esegui prima 'salva', altrimenti verrebbero sovrascritti.")
        sys.exit(2)
    mancanti = [n for n in nomi if not os.path.exists(os.path.join(CAPITOLI, n + ".md"))]
    cambiati = aggiorna_docx(stato, nomi)
    salva_stato(stato)
    print(json.dumps({"docx_aggiornati": cambiati, "gia_aggiornati": [n for n in nomi if n not in cambiati and n not in mancanti],
                      "non_esistono_in_git": mancanti}, ensure_ascii=False))


def cmd_risolto(a):
    """Dopo aver risolto un conflitto in word/.stato/conflitti/<nome>.md:
    lo salva in Git e rigenera il .docx."""
    stato = carica_stato()
    pull()
    aperti = sorted(os.path.splitext(f)[0] for f in os.listdir(CONFLITTI)) \
        if os.path.isdir(CONFLITTI) else []
    nomi = scegli(a.capitoli) if a.capitoli else aperti
    if not nomi:
        print("Nessun conflitto da risolvere.")
        return
    for nome in nomi:
        f = os.path.join(CONFLITTI, nome + ".md")
        if not os.path.exists(f):
            print("ERRORE: nessun conflitto aperto per", nome)
            sys.exit(1)
        with open(f, encoding="utf-8") as fh:
            if "<<<<<<<" in fh.read():
                print("ERRORE: marcatori di conflitto ancora presenti in", f)
                sys.exit(3)
    for nome in nomi:
        shutil.copyfile(os.path.join(CONFLITTI, nome + ".md"), os.path.join(CAPITOLI, nome + ".md"))
    git("add", "capitoli")
    if git("diff", "--cached", "--quiet", check=False).returncode != 0:
        git("commit", "-m", a.messaggio or ("Risolto conflitto: " + ", ".join(nomi)))
        if ha_remoto():
            git("push")
    for nome in nomi:
        rigenera(nome, stato)
        os.remove(os.path.join(CONFLITTI, nome + ".md"))
    salva_stato(stato)
    print(json.dumps({"risolti": nomi}, ensure_ascii=False))


def cmd_salva(a):
    import importa_docx as imp

    stato = carica_stato()
    nomi = scegli(a.capitoli)
    mancanti = [n for n in nomi if not os.path.exists(os.path.join(WORD, n + ".docx"))]
    if mancanti:
        print("ERRORE: non trovo in word/:", ", ".join(m + ".docx" for m in mancanti))
        sys.exit(1)
    mod = [n for n in docx_modificati(stato) if n in nomi]
    # 1. converto i .docx modificati PRIMA di scaricare, in file temporanei
    tmpdir = tempfile.mkdtemp()
    locali = {}
    for nome in mod:
        t = os.path.join(tmpdir, nome + ".md")
        imp.convert(os.path.join(WORD, nome + ".docx"), t)
        locali[nome] = t
    # 2. scarico le modifiche fatte sull'altro PC
    pull()
    # 3. scrivo i .md, unendo se il capitolo e' cambiato anche altrove
    conflitti, uniti = [], []
    os.makedirs(CAPITOLI, exist_ok=True)
    for nome, t in locali.items():
        md = os.path.join(CAPITOLI, nome + ".md")
        base = base_path(nome)
        remoto_cambiato = os.path.exists(md) and (
            not os.path.exists(base) or sha(md) != sha(base))
        if not remoto_cambiato:
            shutil.copyfile(t, md)
            continue
        vuoto = os.path.join(tmpdir, "vuoto.md")
        open(vuoto, "w").close()
        r = subprocess.run(["git", "merge-file", "-L", "Word (questo PC)", "-L", "base",
                            "-L", "Git (altro PC)", t, base if os.path.exists(base) else vuoto, md],
                           capture_output=True, text=True, creationflags=SENZA_FINESTRA)
        if r.returncode != 0:
            # il capitolo in Git resta intatto; la versione con i marcatori va a parte
            os.makedirs(CONFLITTI, exist_ok=True)
            shutil.copyfile(t, os.path.join(CONFLITTI, nome + ".md"))
            conflitti.append(nome)
        else:
            shutil.copyfile(t, md)
            uniti.append(nome)
    for nome in conflitti:
        del locali[nome]
    # 4. commit e push
    git("add", "capitoli")
    fatto = False
    if git("diff", "--cached", "--quiet", check=False).returncode != 0:
        git("commit", "-m", a.messaggio or "Aggiornamento capitoli")
        fatto = True
        if ha_remoto():
            git("push")
    # 5. aggiorno lo stato: i .docx salvati corrispondono ora ai loro .md
    for nome in locali:
        if nome in uniti:
            rigenera(nome, stato)  # il .docx deve includere le modifiche unite
        else:
            md = os.path.join(CAPITOLI, nome + ".md")
            shutil.copyfile(md, base_path(nome))
            stato[nome] = {"docx": sha(os.path.join(WORD, nome + ".docx")), "md": sha(md)}
    salva_stato(stato)
    shutil.rmtree(tmpdir, ignore_errors=True)
    print(json.dumps({"salvati": list(locali),
                      "senza_modifiche": [n for n in nomi if n not in locali and n not in conflitti],
                      "uniti_con_altro_pc": uniti, "conflitti": conflitti, "commit": fatto},
                     ensure_ascii=False))
    if conflitti:
        print("Conflitto: le due versioni sono in word/.stato/conflitti/ tra i marcatori "
              "<<<<<<< ======= >>>>>>>. Il capitolo in Git non e' stato modificato.")
        sys.exit(3)


def ramo_corrente():
    return git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def ramo_principale():
    """Il ramo con la versione completa: main, master o quello indicato dal remoto."""
    r = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", check=False).stdout.strip()
    if r.startswith("origin/"):
        return r[len("origin/"):]
    for n in ("main", "master"):
        if git("rev-parse", "--verify", n, check=False).returncode == 0:
            return n
    return ramo_corrente()


def nome_ramo(v):
    v = str(v).strip().lower()
    if v in ("main", "master", "principale", "completa"):
        return ramo_principale()
    return v if v.startswith("versione-") else "versione-" + v


def file_aperti():
    """Capitoli aperti in LibreOffice o Word (non vanno toccati)."""
    out = []
    for n in tutti_i_nomi():
        if os.path.exists(os.path.join(WORD, f".~lock.{n}.docx#")) or \
                os.path.exists(os.path.join(WORD, "~$" + n[2:] + ".docx")):
            out.append(n)
    return out


def pronto_al_cambio(stato):
    """Blocca il cambio di ramo se ci sono modifiche non salvate o file aperti."""
    mod = docx_modificati(stato)
    aperti = file_aperti()
    if mod or aperti:
        print(json.dumps({"docx_da_salvare": mod, "file_aperti": aperti}, ensure_ascii=False))
        print("Prima di cambiare versione: salva i capitoli modificati e chiudi i file aperti.")
        sys.exit(2)


def cmd_versione(a):
    """Rami di lavoro: una versione del libro per ramo, main = versione completa."""
    stato = carica_stato()
    if a.azione == "elenco":
        rami = set()
        for r in git("branch", "--all", "--format=%(refname:short)").stdout.split():
            r = r.replace("origin/", "")
            if r and r != "origin" and "HEAD" not in r:
                rami.add(r)
        print(json.dumps({"versione_in_uso": ramo_corrente(),
                          "versione_completa": ramo_principale(),
                          "versioni": sorted(rami)}, ensure_ascii=False))
        return
    if not a.versione:
        print("ERRORE: indica la versione (es. 12).")
        sys.exit(1)
    ramo = nome_ramo(a.versione)

    if a.azione == "nuova":
        pronto_al_cambio(stato)
        pull()
        if git("rev-parse", "--verify", ramo, check=False).returncode == 0:
            print(f"ERRORE: il ramo {ramo} esiste gia'. Usa 'versione passa {a.versione}'.")
            sys.exit(1)
        git("checkout", "-q", "-b", ramo)
        if ha_remoto():
            git("push", "-q", "-u", "origin", ramo)
        print(json.dumps({"creata": ramo, "da": ramo_principale(), "ramo_corrente": ramo_corrente()},
                         ensure_ascii=False))
        return

    if a.azione == "passa":
        pronto_al_cambio(stato)
        if ha_remoto():
            git("fetch", "--quiet", check=False)
        if git("rev-parse", "--verify", ramo, check=False).returncode != 0:
            if git("rev-parse", "--verify", "origin/" + ramo, check=False).returncode != 0:
                print(f"ERRORE: la versione {ramo} non esiste. Creala con 'versione nuova {a.versione}'.")
                sys.exit(1)
            git("checkout", "-q", "-b", ramo, "origin/" + ramo)
        else:
            git("checkout", "-q", ramo)
        pull()
        cambiati = aggiorna_docx(stato, tutti_i_nomi())
        salva_stato(stato)
        print(json.dumps({"ramo_corrente": ramo_corrente(), "docx_aggiornati": cambiati},
                         ensure_ascii=False))
        return

    if a.azione == "unisci":
        pronto_al_cambio(stato)
        if ha_remoto():
            git("fetch", "--quiet", check=False)
        if git("rev-parse", "--verify", ramo, check=False).returncode != 0:
            print(f"ERRORE: la versione {ramo} non esiste.")
            sys.exit(1)
        principale = ramo_principale()
        if ramo == principale:
            print("ERRORE: indica la versione da unire nel ramo principale, non il ramo stesso.")
            sys.exit(1)
        git("checkout", "-q", principale)
        pull()
        r = git("merge", "--no-ff", "-m", a.messaggio or f"Unita la {ramo} in {principale}", ramo,
                check=False)
        if r.returncode != 0:
            git("merge", "--abort", check=False)
            sys.stderr.write(r.stdout + r.stderr)
            print(json.dumps({"errore": "conflitto", "ramo": ramo}, ensure_ascii=False))
            print("I due rami hanno cambiato gli stessi passaggi: l'unione e' stata annullata. "
                  "Chiedi a Claude di unirli capitolo per capitolo.")
            sys.exit(3)
        if ha_remoto():
            git("push", "-q")
        cambiati = aggiorna_docx(stato, tutti_i_nomi())
        salva_stato(stato)
        print(json.dumps({"unita": ramo, "ramo_corrente": ramo_corrente(),
                          "docx_aggiornati": cambiati}, ensure_ascii=False))
        return


def cmd_libro(a):
    """Assembla il libro dai capitoli salvati in Git (versione piu' recente)."""
    pull()
    files = sorted(glob.glob(os.path.join(CAPITOLI, "*.md")))
    if a.capitoli:
        nomi = scegli(a.capitoli)
        files = [f for f in files if os.path.splitext(os.path.basename(f))[0] in nomi]
    if not files:
        print("ERRORE: nessun capitolo in capitoli/")
        sys.exit(1)
    out = os.path.join(RADICE, "esporta", a.nome + ".docx")
    try:
        esp.esporta(files, out)
    except PermissionError:
        print(f"ERRORE: {a.nome}.docx e' aperto in Word. Chiudilo e riprova.")
        sys.exit(1)
    print(json.dumps({"creato": out,
                      "capitoli": [os.path.splitext(os.path.basename(f))[0] for f in files],
                      "modifiche_word_non_salvate_escluse": docx_modificati(carica_stato())},
                     ensure_ascii=False))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    ap = sub.add_parser("apri")
    ap.add_argument("capitoli", nargs="*")
    ap.set_defaults(f=cmd_apri)
    sub.add_parser("stato").set_defaults(f=cmd_stato)
    sub.add_parser("elenco").set_defaults(f=cmd_elenco)
    s = sub.add_parser("salva")
    s.add_argument("capitoli", nargs="*")
    s.add_argument("-m", "--messaggio", default="")
    s.set_defaults(f=cmd_salva)
    r = sub.add_parser("risolto")
    r.add_argument("capitoli", nargs="*")
    r.add_argument("-m", "--messaggio", default="")
    r.set_defaults(f=cmd_risolto)
    v = sub.add_parser("versione")
    v.add_argument("azione", choices=["elenco", "nuova", "passa", "unisci"])
    v.add_argument("versione", nargs="?")
    v.add_argument("-m", "--messaggio", default="")
    v.set_defaults(f=cmd_versione)
    lb = sub.add_parser("libro")
    lb.add_argument("capitoli", nargs="*", help="solo questi capitoli (default: tutti)")
    lb.add_argument("--nome", default="libro", help="nome del file in esporta/")
    lb.set_defaults(f=cmd_libro)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
