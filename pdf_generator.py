"""
Generazione PDF visura catastale - struttura ufficiale Agenzia delle Entrate.
A4 landscape. Colonne reali tratte dalla risposta SISTER.
"""

import os
import re
import tempfile
from datetime import datetime

import requests
from fpdf import FPDF

# ── Logo ──────────────────────────────────────────────────────────────────────

_LOGO_LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo_ae.png")
_LOGO_URL   = "https://upload.wikimedia.org/wikipedia/commons/b/b2/Logo_Agenzia_Entrate.png"
_logo_cache = None


def _logo_path() -> str | None:
    global _logo_cache
    if _logo_cache and os.path.exists(_logo_cache):
        return _logo_cache
    if os.path.exists(_LOGO_LOCAL):
        _logo_cache = _LOGO_LOCAL
        return _logo_cache
    try:
        r = requests.get(_LOGO_URL, timeout=8)
        r.raise_for_status()
        fd, p = tempfile.mkstemp(suffix=".png")
        with os.fdopen(fd, "wb") as f:
            f.write(r.content)
        _logo_cache = p
        return p
    except Exception:
        return None


# ── Testo sicuro per Helvetica (Latin-1) ──────────────────────────────────────

_SUBS = {
    "\u2014": "-", "\u2013": "-",
    "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"',
    "\u2026": "...", "\u20ac": "EUR",
    "\u00b0": " ",
}


def s(v) -> str:
    if v is None:
        return ""
    t = str(v)
    for c, r in _SUBS.items():
        t = t.replace(c, r)
    return t.encode("latin-1", errors="replace").decode("latin-1").strip()


def field(d: dict, *keys, default: str = "") -> str:
    for k in keys:
        v = d.get(k)
        if v is not None and str(v).strip() not in ("", "-", "None"):
            return s(str(v).strip())
    return default


def trunc(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 1] + "~"


# ── Costanti layout ───────────────────────────────────────────────────────────

# A4 landscape: 297 x 210 mm   margini 10 mm   →   utile 277 mm
PAGE_W  = 277   # larghezza utile
LM      = 10    # left margin
RH      = 5.0   # altezza riga dati
HH      = 5.0   # altezza riga intestazione colonne
GH      = 5.0   # altezza riga gruppo
FS      = 6.5   # font size tabella

# Larghezze colonne (totale deve essere == PAGE_W = 277)
CW = {
    "n":        7,
    "sez":      9,
    "foglio":  13,
    "numero":  15,
    "sub":     10,
    "zona":    13,
    "micro":   13,
    "cat":     16,
    "cla":     11,
    "con":     22,
    "sup":     19,
    "ren":     27,
    "ind":     83,
    "ult":     19,
}
# Check: sum = 7+9+13+15+10+13+13+16+11+22+19+27+83+19 = 277 ✓

# Raggruppamenti per intestazione
G_IDENT = CW["sez"] + CW["foglio"] + CW["numero"] + CW["sub"] + CW["zona"] + CW["micro"]  # 73
G_CLASS = CW["cat"] + CW["cla"] + CW["con"] + CW["sup"] + CW["ren"]                        # 95
G_ALTRE = CW["ind"] + CW["ult"]                                                              # 102
# CW["n"] + G_IDENT + G_CLASS + G_ALTRE = 7+73+95+102 = 277 ✓


# ── Classe PDF ────────────────────────────────────────────────────────────────

class VisuraPDF(FPDF):

    def __init__(self, provincia: str, comune: str, tipo_label: str,
                 data_oggi: str, ora_oggi: str, visura_n: str):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(LM, 10, LM)
        self._prov   = s(provincia)
        self._comune = s(comune)
        self._tipo   = s(tipo_label)
        self._data   = data_oggi
        self._ora    = ora_oggi
        self._vnum   = s(visura_n)
        self._logo   = _logo_path()
        self._pgn    = 0

    # ── Intestazione pagina ────────────────────────────────────────────────────

    def header(self):
        self._pgn += 1

        # Logo top-left  (aspect 3603:1017 ≈ 3.54 → h=15 ⟹ w≈53 mm)
        logo_right = LM   # x dove finisce il logo (sarà aggiornato se caricato)
        if self._logo:
            try:
                self.image(self._logo, x=LM, y=8, h=15)
                logo_right = LM + int(15 * 3603 / 1017) + 2
            except Exception:
                logo_right = LM

        # Ufficio sotto logo
        self.set_xy(LM, 24)
        self.set_font("Helvetica", "", 6)
        self.set_text_color(60, 60, 60)
        self.cell(60, 3.5, s(f"Direzione Provinciale di {self._prov}"))
        self.ln(3.5)
        self.set_x(LM)
        self.cell(60, 3.5, "Ufficio Provinciale - Territorio")
        self.ln(3.5)
        self.set_x(LM)
        self.cell(60, 3.5, "Servizi Catastali")

        # Data / Ora / Pagina — top right
        self.set_font("Helvetica", "", 7)
        self.set_text_color(60, 60, 60)
        self.set_xy(LM + PAGE_W - 55, 8)
        self.cell(55, 4, f"Data: {self._data}  Ora: {self._ora}  pag: {self._pgn}", align="R")
        self.set_xy(LM + PAGE_W - 55, 13)
        self.cell(55, 4, f"Visura n.: {self._vnum}", align="R")

        # Titolo centrato tra logo e data
        title_x = logo_right + 2
        title_w = (LM + PAGE_W - 55) - title_x - 2
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(0, 0, 0)
        self.set_xy(title_x, 9)
        self.cell(title_w, 8, "Visura attuale sintetica per soggetto", align="C")

        self.set_font("Helvetica", "", 9)
        self.set_xy(title_x, 18)
        self.cell(title_w, 5, f"Situazione degli atti informatizzati al {self._data}", align="C")

        # Linea separatrice
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.4)
        self.line(LM, 36, LM + PAGE_W, 36)
        self.set_text_color(0, 0, 0)
        self.set_y(39)

    def footer(self):
        self.set_y(-10)
        self.set_font("Helvetica", "I", 6)
        self.set_text_color(120, 120, 120)
        self.cell(0, 4, "Documento generato tramite S.I.S.T.E.R. - Non ha valore di certificato ufficiale.", align="C")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _info_row(self, label: str, value: str):
        self.set_x(LM)
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(230, 230, 230)
        self.cell(52, 6, s(label), border=1, fill=True)
        self.set_font("Helvetica", "", 8)
        self.cell(PAGE_W - 52, 6, s(value), border=1, ln=True)

    def _section(self, text: str):
        self.ln(2)
        self.set_x(LM)
        self.set_font("Helvetica", "B", 8.5)
        self.cell(0, 6, s(text), ln=True)

    # ── Intestazioni tabella immobili ─────────────────────────────────────────

    def table_header(self):
        self.set_x(LM)
        self.set_font("Helvetica", "B", FS)
        self.set_fill_color(195, 195, 195)
        self.set_text_color(0, 0, 0)

        # Riga 1 — gruppi
        self.cell(CW["n"], GH, "",                    border=1, fill=True)
        self.cell(G_IDENT,  GH, "DATI IDENTIFICATIVI", border=1, fill=True, align="C")
        self.cell(G_CLASS,  GH, "DATI DI CLASSAMENTO", border=1, fill=True, align="C")
        self.cell(G_ALTRE,  GH, "ALTRE INFORMAZIONI",  border=1, fill=True, align="C")
        self.ln(GH)

        # Riga 2 — colonne
        self.set_x(LM)
        self.set_fill_color(215, 215, 215)
        headers = [
            ("N.",          CW["n"]),
            ("Sez.Urb.",    CW["sez"]),
            ("Foglio",      CW["foglio"]),
            ("Numero",      CW["numero"]),
            ("Sub",         CW["sub"]),
            ("Zona Cens.",  CW["zona"]),
            ("Micro Zona",  CW["micro"]),
            ("Categoria",   CW["cat"]),
            ("Classe",      CW["cla"]),
            ("Consistenza", CW["con"]),
            ("Sup.Cat.",    CW["sup"]),
            ("Rendita",     CW["ren"]),
            ("Indirizzo / Dati derivanti da", CW["ind"]),
            ("Dati Ult.",   CW["ult"]),
        ]
        for lbl, w in headers:
            self.cell(w, HH, lbl, border=1, fill=True, align="C")
        self.ln(HH)

    # ── Riga immobile ─────────────────────────────────────────────────────────

    def table_row(self, n: int, imm: dict, alt: bool = False):
        self.set_x(LM)
        self.set_font("Helvetica", "", FS)
        bg = (245, 245, 245) if alt else (255, 255, 255)
        self.set_fill_color(*bg)

        sez     = field(imm, "Sezione", "Sez")
        foglio  = field(imm, "Foglio")
        numero  = field(imm, "Particella", "Numero")
        sub     = field(imm, "Sub", "Subalterno")
        zona    = field(imm, "Zona cens", "ZonaCens")
        micro   = field(imm, "Micro Zona")
        cat     = field(imm, "Categoria")
        cla     = field(imm, "Classe")
        con     = field(imm, "Consistenza")
        sup     = field(imm, "Superficie Catastale", "SuperficieCatastale")
        ren     = field(imm, "Rendita", "Rendita Catastale")
        indirizzo = field(imm, "Indirizzo", "Via", "Localita")
        altri   = field(imm, "Altri Dati")
        ind_str = (indirizzo + " - " + altri).strip(" -") if altri else indirizzo

        # Calcola quante righe occupa l'indirizzo per capire l'altezza cella
        chars_per_line = int(CW["ind"] / 1.85)  # ~1.85mm per carattere a 6.5pt
        ind_lines = max(1, -(-len(ind_str) // chars_per_line))  # ceil div
        row_h = max(RH, RH * ind_lines)

        # Celle fisse (altezza fissa = row_h, non wrappano)
        fixed = [
            (str(n), CW["n"]),
            (sez,    CW["sez"]),
            (foglio, CW["foglio"]),
            (numero, CW["numero"]),
            (sub,    CW["sub"]),
            (zona,   CW["zona"]),
            (micro,  CW["micro"]),
            (cat,    CW["cat"]),
            (cla,    CW["cla"]),
            (con,    CW["con"]),
            (sup,    CW["sup"]),
            (ren,    CW["ren"]),
        ]
        y0 = self.get_y()
        for val, w in fixed:
            self.cell(w, row_h, trunc(val, int(w / 1.5)), border=1, fill=alt, align="C")

        # Indirizzo: multi_cell che wrappa
        x_ind = self.get_x()
        self.set_xy(x_ind, y0)
        self.multi_cell(CW["ind"], RH, s(ind_str), border=1, fill=alt, align="L")
        actual_h = self.get_y() - y0

        # Dati ulteriori
        self.set_xy(x_ind + CW["ind"], y0)
        self.cell(CW["ult"], actual_h, "", border=1, fill=alt, align="C")

        # Assicura che le celle fisse abbiano altezza pari ad actual_h
        # (ridisegna i bordi se la multi_cell ha wrappato più del previsto)
        if actual_h > row_h:
            # ridisegna la porzione destra dei bordi delle celle fisse
            x_cur = LM
            for _, w in fixed:
                self.rect(x_cur, y0, w, actual_h)
                x_cur += w

        self.set_y(y0 + actual_h)

    # ── Tabella intestatari ───────────────────────────────────────────────────

    def intestatari_header(self):
        self.ln(2)
        self.set_x(LM)
        self.set_font("Helvetica", "B", 7.5)
        self.cell(0, 5, "Intestazione degli immobili indicati al n.1", ln=True)

        self.set_x(LM)
        self.set_font("Helvetica", "B", 7)
        self.set_fill_color(210, 210, 210)
        self.cell(8,   5, "N.",               border=1, fill=True, align="C")
        self.cell(103, 5, "DATI ANAGRAFICI",  border=1, fill=True, align="C")
        self.cell(46,  5, "CODICE FISCALE",   border=1, fill=True, align="C")
        self.cell(120, 5, "DIRITTI E ONERI REALI", border=1, fill=True, align="C", ln=True)

    def intestatario_row(self, n: int, sog: dict):
        self.set_x(LM)
        self.set_font("Helvetica", "", 7)
        y0 = self.get_y()

        nome    = field(sog, "Nominativo o denominazione", "Soggetto", "Nome", "Cognome e Nome", "Denominazione")
        cf      = field(sog, "Codice fiscale", "Codice Fiscale", "CF", "CodiceFiscale")
        diritto = field(sog, "Titolarita", "Titolarità", "Titolo", "Diritto", "Tipo Diritto")
        quota   = field(sog, "Quota", "Quota Possesso")
        regime  = field(sog, "Altri dati", "Regime Patrimoniale", "Regime")

        diritti = " ".join(filter(None, [diritto, quota, regime]))

        self.cell(8, 5, str(n), border=1, align="C")
        x_an = self.get_x()
        self.set_xy(x_an, y0)
        self.multi_cell(103, 5, s(nome), border=1)
        h = self.get_y() - y0
        self.set_xy(x_an + 103, y0)
        self.cell(46,  h, s(cf),      border=1, align="C")
        self.cell(120, h, s(diritti), border=1)
        self.set_y(y0 + h)


# ── Funzione pubblica ─────────────────────────────────────────────────────────

def genera_pdf_visura(
    provincia: str,
    comune: str,
    foglio: str,
    particella: str,
    tipo_catasto: str,
    data: dict,
) -> bytes:
    tipo_label = "Fabbricati" if tipo_catasto == "F" else "Terreni"
    now        = datetime.now()
    data_oggi  = now.strftime("%d/%m/%Y")
    ora_oggi   = now.strftime("%H.%M.%S")
    visura_n   = f"T{now.strftime('%d%m%y')}/2026"

    pdf = VisuraPDF(
        provincia  = provincia,
        comune     = comune,
        tipo_label = tipo_label,
        data_oggi  = data_oggi,
        ora_oggi   = ora_oggi,
        visura_n   = visura_n,
    )
    pdf.add_page()

    immobili  = data.get("immobili", [])
    intestati = data.get("intestati", [])

    # ── Dati richiesta ────────────────────────────────────────────────────────
    pdf._info_row(
        "Dati della richiesta",
        s(f"Catasto dei {tipo_label} - Comune di {comune.upper()} - Foglio {foglio} - Particella {particella}"),
    )
    pdf.ln(1)

    # ── Sezione 1: immobili ───────────────────────────────────────────────────
    pdf._section(
        f"1. Immobili siti nel Comune di {s(comune.upper())}   Catasto dei {tipo_label}"
    )
    pdf.table_header()

    totale_rendita = 0.0
    for idx, imm in enumerate(immobili, 1):
        ren_raw = field(imm, "Rendita", "Rendita Catastale")
        try:
            nums = re.findall(r"[\d]+[,.][\d]+", ren_raw.replace(".", "").replace(",", "."))
            if nums:
                totale_rendita += float(nums[0])
        except Exception:
            pass
        pdf.table_row(idx, imm, alt=(idx % 2 == 0))

    pdf.ln(2)

    # Totale rendita
    ren_fmt = f"{totale_rendita:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    pdf.set_x(LM)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(0, 5,
        f"Rendita totale: Euro {ren_fmt}    Unita immobiliari n. {len(immobili)}",
        ln=True)
    pdf.ln(2)

    # ── Sezione 2: intestatari ────────────────────────────────────────────────
    if intestati:
        pdf.intestatari_header()
        for idx, sog in enumerate(intestati, 1):
            pdf.intestatario_row(idx, sog)
        pdf.ln(2)

    # ── Totale generale ───────────────────────────────────────────────────────
    pdf.set_x(LM)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, f"Totale Generale:   Rendita: Euro {ren_fmt}", ln=True)
    pdf.ln(1)
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(0, 4, f"Unita immobiliari n. {len(immobili)}", ln=True)
    pdf.ln(5)

    # ── Note legali ───────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "I", 6.5)
    pdf.set_text_color(80, 80, 80)
    pdf.set_x(LM)
    pdf.multi_cell(
        PAGE_W, 3.5,
        "* Codice Fiscale Validato in Anagrafe Tributaria\n"
        "** Si intendono escluse le \"superfici di balconi, terrazzi e aree scoperte pertinenziali e accessorie, "
        "comunicanti o non comunicanti\" (cfr. Provvedimento del Direttore dell'Agenzia delle Entrate 29 marzo 2013).\n"
        "Documento generato tramite interrogazione telematica del Sistema Informativo S.I.S.T.E.R. - "
        "Non ha valore di certificato ufficiale.",
    )

    return bytes(pdf.output())
