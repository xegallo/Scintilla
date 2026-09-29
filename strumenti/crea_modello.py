#!/usr/bin/env python3
"""Crea strumenti/modello.docx (modello di stile per pandoc) a partire da un
capitolo .docx originale: ne conserva pagina, margini, intestazioni e piè di
pagina, e definisce gli stili con nome usati dall'esportazione.

Uso:  python crea_modello.py "Capitolo_00.docx" strumenti/modello.docx

Per cambiare l'aspetto del libro basta aprire modello.docx in Word e
modificare gli stili (Corpo, Documento, ecc.): non serve toccare questo file.
"""
import re
import sys
import zipfile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def rpr(font="Arial", sz=21, color=None, b=False, i=False, spacing=None):
    x = f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}" w:eastAsia="{font}"/>'
    x += "<w:b/><w:bCs/>" if b else ""
    x += "<w:i/><w:iCs/>" if i else ""
    x += f'<w:color w:val="{color}"/>' if color else ""
    x += f'<w:spacing w:val="{spacing}"/>' if spacing else ""
    x += f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
    return f"<w:rPr>{x}</w:rPr>"


def ppr(jc="both", before=0, after=0, line=None, first=None, left=None, right=None,
        border=None, keep=False):
    x = "<w:keepNext/>" if keep else ""
    x += f"<w:pBdr>{border}</w:pBdr>" if border else ""
    sp = f'w:before="{before}" w:after="{after}"'
    if line:
        sp += f' w:line="{line}" w:lineRule="auto"'
    x += f"<w:spacing {sp}/>"
    ind = ""
    if left is not None:
        ind += f' w:left="{left}"'
    if right is not None:
        ind += f' w:right="{right}"'
    if first is not None:
        ind += f' w:firstLine="{first}"'
    x += f"<w:ind{ind}/>" if ind else ""
    x += f'<w:jc w:val="{jc}"/>'
    return f"<w:pPr>{x}</w:pPr>"


def style(sid, name, p, r, based="Normal", nxt=None):
    n = f'<w:next w:val="{nxt}"/>' if nxt else ""
    return (f'<w:style w:type="paragraph" w:customStyle="1" w:styleId="{sid}">'
            f'<w:name w:val="{name}"/><w:basedOn w:val="{based}"/>{n}<w:qFormat/>{p}{r}</w:style>')


BORDO_SX = '<w:left w:val="single" w:sz="6" w:space="12" w:color="BFBFBF"/>'
BORDO_SOTTO = '<w:bottom w:val="single" w:sz="6" w:space="6" w:color="9A9A9A"/>'

STILI = {
    # id: (nome, pPr, rPr)
    "Corpo": ("Corpo", ppr(line=300, first=283), rpr()),
    "Corposenzarientro": ("Corpo senza rientro", ppr(line=300, first=0), rpr()),
    "Etichettacapitolo": ("Etichetta capitolo",
                          ppr(jc="center", before=1984, after=120, keep=True),
                          rpr(sz=19, color="808080", b=True, spacing=100)),
    "Sottotitolocapitolo": ("Sottotitolo capitolo",
                            ppr(jc="center", before=0, after=680, keep=True),
                            rpr(sz=19, color="707070", i=True)),
    "Nota": ("Nota", ppr(jc="left", before=200, after=200, line=280, left=907),
             rpr(sz=20, color="2A2A2A", i=True)),
    "Documentotitolo": ("Documento titolo",
                        ppr(jc="left", before=320, after=100, left=453, right=453,
                            border=BORDO_SOTTO, keep=True),
                        rpr(font="Roboto", sz=19, color="3C3C3C", b=True, spacing=30)),
    "Documento": ("Documento",
                  ppr(before=80, after=0, line=260, left=453, right=453, border=BORDO_SX),
                  rpr(font="Roboto", sz=19, color="2A2A2A")),
    "Documentocontinua": ("Documento continua",
                          ppr(before=0, after=0, line=260, left=453, right=453, border=BORDO_SX),
                          rpr(font="Roboto", sz=19, color="2A2A2A")),
}

HEADING1 = ('<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>'
            '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>'
            + ppr(jc="center", before=0, after=793, keep=True).replace("</w:pPr>", '<w:outlineLvl w:val="0"/></w:pPr>')
            + rpr(sz=40, color="000000", b=True) + "</w:style>")


def main(src, dst):
    zin = zipfile.ZipFile(src)
    zout = zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED)
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == "word/document.xml":
            s = data.decode("utf8")
            # corpo vuoto: resta solo l'impostazione di pagina (sectPr)
            sect = re.search(r"<w:sectPr\b.*</w:sectPr>", s, re.S).group(0)
            s = re.sub(r"<w:body>.*</w:body>",
                       lambda m: f"<w:body><w:p/>{sect}</w:body>", s, flags=re.S)
            data = s.encode("utf8")
        elif item.filename == "word/styles.xml":
            s = data.decode("utf8")
            s = re.sub(r'<w:style [^>]*w:styleId="Heading1".*?</w:style>', HEADING1, s, flags=re.S)
            for sid in STILI:
                s = re.sub(rf'<w:style [^>]*w:styleId="{sid}".*?</w:style>', "", s, flags=re.S)
            extra = "".join(style(sid, *v) for sid, v in STILI.items())
            s = s.replace("</w:styles>", extra + "</w:styles>")
            data = s.encode("utf8")
        elif re.fullmatch(r"word/header\d+\.xml", item.filename):
            s = data.decode("utf8")
            # la testatina delle pagine dispari diventa un segnaposto per capitolo
            if 'w:jc w:val="right"' in s:
                s = re.sub(r"(<w:t[^>]*>)[^<]*(</w:t>)", r"\1{{TESTATINA}}\2", s)
            data = s.encode("utf8")
        zout.writestr(item, data)
    zout.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
