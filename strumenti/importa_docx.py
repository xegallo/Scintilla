#!/usr/bin/env python3
"""Converte un capitolo .docx (formato attuale) in Markdown.

Uso:  python importa_docx.py "Capitolo_00_-_Prologo.docx" capitoli/00-prologo.md

Regole ricavate dai file originali:
  - 1a riga centrata maiuscola      -> <etichetta>...</etichetta>
  - Heading 1                       -> # Titolo
  - riga centrata in corsivo        -> <sottotitolo>...</sottotitolo>
  - corpo con rientro prima riga    -> inizio di un nuovo blocco (riga vuota prima)
  - corpo senza rientro             -> riga che continua il blocco (a capo semplice)
  - corsivo rientrato a sinistra    -> <nota> ... </nota>
  - paragrafo con bordo inferiore   -> <documento> TITOLO ... </documento>
  - paragrafi con bordo sinistro    -> righe del documento
Richiede: pip install python-docx
"""
import re
import sys

import docx
from docx.oxml.ns import qn


def pstyle(p):
    ppr = p._p.pPr
    return ppr.pStyle.val if ppr is not None and ppr.pStyle is not None else ""


def has_border(p, side):
    ppr = p._p.pPr
    if ppr is None:
        return False
    bdr = ppr.find(qn("w:pBdr"))
    return bdr is not None and bdr.find(qn(side)) is not None


def inline_md(p):
    """Testo del paragrafo con *corsivo* e **grassetto**; <w:br/> -> '\n'."""
    segs = []  # (testo, italic, bold)
    for r in p.runs:
        txt = ""
        for el in r._r:
            if el.tag == qn("w:t"):
                txt += el.text or ""
            elif el.tag in (qn("w:br"), qn("w:cr")):
                txt += "\n"
            elif el.tag == qn("w:tab"):
                txt += "\t"
        if not txt:
            continue
        seg = (escapa(txt), bool(r.italic), bool(r.bold))
        if segs and segs[-1][1:] == seg[1:]:
            segs[-1] = (segs[-1][0] + txt,) + seg[1:]
        else:
            segs.append(seg)
    out = ""
    for txt, it, bd in segs:
        mark = ("**" if bd else "") + ("*" if it else "")
        if not mark:
            out += txt
            continue
        # gli spazi restano fuori dai marcatori
        lead = re.match(r"^\s*", txt).group()
        trail = re.search(r"\s*$", txt).group()
        core = txt.strip()
        out += lead + (mark + core + mark[::-1] if core else "") + trail
    return out


SPECIALI = str.maketrans({c: "\\" + c for c in "\\*_`<>[]"})


def escapa(t):
    """Protegge i caratteri che il Markdown interpreterebbe come formattazione."""
    return t.translate(SPECIALI)


def escapa_inizio(md):
    """Protegge un carattere a inizio riga (es. '- ', '# ', '1. ') senza toccare
    i marcatori di corsivo/grassetto gia' aggiunti."""
    pre = re.match(r"^\*{0,3}", md).group(0)
    resto = md[len(pre):]
    if re.match(r"^[#+=|~-]", resto):
        return pre + "\\" + resto
    m = re.match(r"^(\d+)([.)])", resto)
    if m:
        return pre + m.group(1) + "\\" + resto[m.end(1):]
    return md


def strip_wrap(md):
    """Toglie * o ** che avvolgono l'intera riga: lo stile li applica gia'."""
    m = re.fullmatch(r"(\*{1,3})([^*]+)\1", md)
    return m.group(2) if m else md


def space_before(p):
    if pstyle(p) == "Documento":
        return True
    v = p.paragraph_format.space_before
    return v is not None and v > 0


# stessi elementi riconosciuti dal nome di stile (file generati da esporta.py)
def is_doc_title(p):
    return pstyle(p) == "Documentotitolo" or has_border(p, "w:bottom")


def is_doc_line(p):
    return pstyle(p) in ("Documento", "Documentocontinua") or has_border(p, "w:left")


def is_nota(p):
    return pstyle(p) == "Nota" or (p.paragraph_format.left_indent or 0) > 0


def rientro(p):
    st = pstyle(p)
    if st == "Corpo":
        return 1
    if st == "Corposenzarientro":
        return 0
    return p.paragraph_format.first_line_indent or 0


def convert(src, dst):
    d = docx.Document(src)
    paras = [p for p in d.paragraphs if p.text.strip()]
    meta = {}
    i = 0
    # apertura capitolo
    if paras and (pstyle(paras[0]) == "Etichettacapitolo" or
                  (paras[0].alignment == 1 and pstyle(paras[0]) != "Heading1")):
        meta["etichetta"] = paras[0].text.strip().capitalize()
        i = 1
    if i < len(paras) and pstyle(paras[i]).startswith("Heading"):
        meta["titolo"] = paras[i].text.strip()
        i += 1
    if i < len(paras) and (pstyle(paras[i]) == "Sottotitolocapitolo" or
                           (paras[i].alignment == 1 and any(r.italic for r in paras[i].runs))):
        meta["sottotitolo"] = paras[i].text.strip()
        i += 1

    lines = []
    if "etichetta" in meta:
        lines.append(f"<etichetta>{meta['etichetta']}</etichetta>")
    if "titolo" in meta:
        lines.append(f"# {meta['titolo']}")
    if "sottotitolo" in meta:
        lines.append(f"<sottotitolo>{meta['sottotitolo']}</sottotitolo>")
    mode = None  # 'corpo' | 'documento' | 'nota'

    def chiudi():
        if mode in ("documento", "nota"):
            while lines and lines[-1] == "":
                lines.pop()
            lines.append(f"</{mode}>")
    for p in paras[i:]:
        md = inline_md(p).strip()
        first = rientro(p)
        if is_doc_title(p):  # titolo documento
            chiudi()
            lines += ["", "<documento>", strip_wrap(md)]
            mode = "documento"
            appena_titolo = True
        elif is_doc_line(p):  # riga di documento
            if mode != "documento":
                chiudi()
                lines += ["", "<documento>", ""]  # riga vuota: documento senza titolo
                mode = "documento"
                appena_titolo = True
            if space_before(p) and not appena_titolo:
                lines.append("")
            appena_titolo = False
            lines.append(escapa_inizio(md))
        elif is_nota(p):  # nota di trascrizione
            chiudi()
            lines += ["", "<nota>"] + [strip_wrap(l.strip()) for l in md.split("\n")]
            mode = "nota"
        else:  # corpo del testo
            chiudi()
            if mode != "corpo" or first > 0:
                lines.append("")
            lines.append(escapa_inizio(md.replace("\n", " ")))
            mode = "corpo"
    chiudi()
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).lstrip("\n") + "\n")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
