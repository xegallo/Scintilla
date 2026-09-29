#!/usr/bin/env python3
"""Esporta i capitoli Markdown in Word con lo stile del libro.

Uso (dalla cartella del libro):
  python strumenti/esporta.py                          -> esporta/libro.docx (tutti i capitoli)
  python strumenti/esporta.py capitoli/00-prologo.md   -> esporta/00-prologo.docx

Richiede solo pandoc (https://pandoc.org) e Python 3, nessuna libreria aggiuntiva.
Ogni capitolo inizia su una nuova pagina, senza testatina nella prima pagina;
le pagine dispari riportano "Etichetta · Titolo" del capitolo.
"""
import glob
import html
import os
import re
import subprocess
import sys
import tempfile
import zipfile

# su Windows evita che i comandi esterni aprano una finestra nera
SENZA_FINESTRA = 0x08000000 if os.name == "nt" else 0

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
MODELLO = os.path.join(QUI, "modello.docx")
FILTRO = os.path.join(QUI, "libro.lua")


def leggi_capitolo(path):
    with open(path, encoding="utf-8") as f:
        testo = f.read()
    meta = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", testo, re.S)
    if m:
        for riga in m.group(1).splitlines():
            if ":" in riga:
                k, v = riga.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
        testo = testo[m.end():]
    return da_tag(meta, testo)


TAG_RIGA = re.compile(r"^\s*<(etichetta|sottotitolo)>(.*?)</\1>\s*$", re.M)
TAG_APRE = re.compile(r"^\s*<([a-zà-ù]+)>\s*$")
TAG_CHIUDE = re.compile(r"^\s*</([a-zà-ù]+)>\s*$")


def da_tag(meta, testo):
    """Traduce la sintassi a tag nella forma interna usata dal filtro.

    <etichetta>Prologo</etichetta>      -> etichetta del capitolo
    # Titolo                            -> titolo del capitolo (primo titolo del file)
    <sottotitolo>...</sottotitolo>      -> sottotitolo
    <documento> ... </documento>        -> inserto; la prima riga e' il titolo
    <nota> ... </nota>                  -> nota (nessun titolo)
    """
    for m in TAG_RIGA.finditer(testo):
        meta.setdefault(m.group(1), m.group(2).strip())
    testo = TAG_RIGA.sub("", testo)
    if "titolo" not in meta:
        m = re.search(r"^#\s+(.+?)\s*$", testo, re.M)
        if m:
            meta["titolo"] = m.group(1)
            testo = testo[:m.start()] + testo[m.end():]

    out, tipo, prima = [], None, False
    for riga in testo.split("\n"):
        if tipo is None:
            m = TAG_APRE.match(riga)
            if m:
                tipo, prima = m.group(1), True
                out += ["", f"> [!{tipo}]"]
                continue
            out.append(riga)
        else:
            if TAG_CHIUDE.match(riga):
                tipo = None
                out.append("")
                continue
            if prima:
                prima = False
                if not riga.strip():  # riga vuota subito dopo il tag: nessun titolo
                    continue
                if tipo != "nota":  # la prima riga e' il titolo dell'inserto
                    out[-1] += " " + riga.strip()
                    continue
            out.append("> " + riga if riga.strip() else ">")
    return meta, "\n".join(out)


def attr(v):
    return v.replace("\\", "\\\\").replace('"', '\\"')


def componi(files):
    parti, testatine = [], []
    for path in files:
        meta, corpo = leggi_capitolo(path)
        titolo = meta.get("titolo", os.path.splitext(os.path.basename(path))[0])
        etichetta = meta.get("etichetta", "")
        parti.append(
            f'::: {{.apertura etichetta="{attr(etichetta)}" sottotitolo="{attr(meta.get("sottotitolo", ""))}"}}\n'
            f"# {titolo}\n:::\n\n{corpo.strip()}\n"
        )
        testatine.append(f"{etichetta} · {titolo}" if etichetta else titolo)
    return "\n\n".join(parti), testatine


def sistema_sezioni(docx_path, testatine):
    """Una sezione per capitolo, ognuna con la propria testatina."""
    z = zipfile.ZipFile(docx_path)
    files = {n: z.read(n) for n in z.namelist()}
    z.close()

    doc = files["word/document.xml"].decode("utf8")
    rels = files["word/_rels/document.xml.rels"].decode("utf8")
    ctypes = files["[Content_Types].xml"].decode("utf8")

    inizio = max(doc.rfind("<w:sectPr>"), doc.rfind("<w:sectPr "))
    finale = re.compile(r"<w:sectPr\b[^>]*>(.*?)</w:sectPr>", re.S).search(doc, inizio)
    interno = finale.group(1)
    m = re.search(r'<w:headerReference\b[^>]*w:type="default"[^>]*>', interno)
    if not m:
        return
    rid = re.search(r'r:id="([^"]+)"', m.group(0)).group(1)
    target = re.search(rf'Id="{rid}"[^>]*Target="([^"]+)"', rels) or \
        re.search(rf'Target="([^"]+)"[^>]*Id="{rid}"', rels)
    base_hdr = files["word/" + target.group(1)].decode("utf8")

    nuovi = []
    for i, t in enumerate(testatine, 1):
        nome = f"header_cap{i}.xml"
        files["word/" + nome] = base_hdr.replace("{{TESTATINA}}", html.escape(t, quote=False)).encode("utf8")
        nid = f"rIdCap{i}"
        rels = rels.replace("</Relationships>",
                            f'<Relationship Id="{nid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="{nome}"/></Relationships>')
        ctypes = ctypes.replace("</Types>",
                                f'<Override PartName="/word/{nome}" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/></Types>')
        sez = interno.replace(f'r:id="{rid}"', f'r:id="{nid}"')
        if i > 1:  # la numerazione continua dal capitolo precedente
            sez = re.sub(r"<w:pgNumType[^>]*/>", "", sez)
        nuovi.append(sez)

    # sezioni intermedie (segnaposto inseriti dal filtro) e sezione finale
    s, e = finale.span(1)
    doc = doc[:s] + nuovi[-1] + doc[e:]
    for sez in nuovi[:-1]:
        doc = doc.replace("{{SEZIONE}}", sez, 1)

    files["word/document.xml"] = doc.encode("utf8")
    files["word/_rels/document.xml.rels"] = rels.encode("utf8")
    files["[Content_Types].xml"] = ctypes.encode("utf8")
    # pandoc aggiunge copie vuote degli stili personalizzati: tengo la prima
    stili = files["word/styles.xml"].decode("utf8")
    visti = set()

    def dedup(mm):
        sid = re.search(r'w:styleId="([^"]+)"', mm.group(0)).group(1)
        if sid in visti:
            return ""
        visti.add(sid)
        return mm.group(0)
    stili = re.sub(r"<w:style\b.*?</w:style>", dedup, stili, flags=re.S)
    files["word/styles.xml"] = stili.encode("utf8")

    sett = files["word/settings.xml"].decode("utf8")
    if "evenAndOddHeaders" not in sett:
        sett = re.sub(r"(<w:settings[^>]*>)", r"\1<w:evenAndOddHeaders/>", sett, count=1)
        files["word/settings.xml"] = sett.encode("utf8")

    with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", files.pop("[Content_Types].xml"))
        for n, d in files.items():
            z.writestr(n, d)


def esporta(files, out):
    """Crea il file Word `out` dai capitoli `files` (lista di percorsi .md)."""
    md, testatine = componi(files)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(md)
    try:
        subprocess.run(["pandoc", tmp.name, "-f", "markdown-smart-auto_identifiers",
                        "-o", out, "--reference-doc", MODELLO, "--lua-filter", FILTRO],
                       check=True, creationflags=SENZA_FINESTRA)
    finally:
        os.unlink(tmp.name)
    sistema_sezioni(out, testatine)
    return out


def main():
    args = sys.argv[1:]
    if args:
        files = args
        nome = os.path.splitext(os.path.basename(args[0]))[0] if len(args) == 1 else "selezione"
    else:
        files = sorted(glob.glob(os.path.join(RADICE, "capitoli", "*.md")))
        nome = "libro"
    if not files:
        sys.exit("Nessun capitolo trovato in capitoli/")
    print("Creato:", esporta(files, os.path.join(RADICE, "esporta", nome + ".docx")))


if __name__ == "__main__":
    main()
