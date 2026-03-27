"""
Management command: import_cao_pdf
Downloadt en parseert de officiële CAO Kinderopvang bijlage 13 diplomalijst (PDF)
en importeert alle erkende diploma's in de database.

Gebruik:
    python manage.py import_cao_pdf
    python manage.py import_cao_pdf --url <eigen_url>   # andere PDF-versie
    python manage.py import_cao_pdf --file /pad/naar/file.pdf
    python manage.py import_cao_pdf --dry-run           # alleen printen, niet opslaan
"""

import re
import tempfile
import requests
from django.core.management.base import BaseCommand
from diplomacheck.models import Diploma

CAO_PDF_URL = (
    "https://www.kinderopvang-werkt.nl/sites/fcb_kinderopvang/files/2025-04/"
    "Bijlage-13-1-Cao-Kinderopvang-Diplomalijst-2025-2026.pdf"
)

# ── Headers zodat kinderopvang-werkt.nl de download toestaat ─────────────────
DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.kinderopvang-werkt.nl/",
}

# ── Regels die geen diplomanamen zijn ─────────────────────────────────────────
SKIP_PATTERNS = [
    re.compile(r"^diplomalijst$", re.I),
    re.compile(r"^diploma\s+valt onder", re.I),
    re.compile(r"^dagopvang en", re.I),
    re.compile(r"^peuteropvang", re.I),
    re.compile(r"^buitenschoolse", re.I),
    re.compile(r"^opvang \(bso\)", re.I),
    re.compile(r"^volgens lijst", re.I),
    re.compile(r"^van categorie", re.I),
    re.compile(r"^als aanvullend bewijs", re.I),
    re.compile(r"^cao kinderopvang", re.I),
    re.compile(r"pagina\s*\|", re.I),
    re.compile(r"^bijlage [IV]+", re.I),
    re.compile(r"^behorend bij", re.I),
    re.compile(r"^hieronder staat", re.I),
    re.compile(r"^ook de diploma", re.I),
    re.compile(r"^het gaat om", re.I),
    re.compile(r"^er staan", re.I),
    re.compile(r"^a:\s+voor de", re.I),
    re.compile(r"^a1\s*=", re.I),
    re.compile(r"^a2\s*=", re.I),
    re.compile(r"^b:\s+", re.I),
    re.compile(r"^b1\s*=", re.I),
    re.compile(r"^b2\s*=", re.I),
    re.compile(r"^binnen a2", re.I),
    re.compile(r"^het overzicht", re.I),
    re.compile(r"^of$", re.I),
    re.compile(r"^•\s+", re.I),
    re.compile(r"^\d+\s+bij hbo", re.I),
    re.compile(r"^de eisen die", re.I),
    re.compile(r"^hoger beroepsonderwijs", re.I),
    # Intro-zin fragmenten die door pagina-omslag uitsijpelen
    re.compile(r"www\.", re.I),
    re.compile(r"dagopvang,\s+de\s+peuteropvang", re.I),
    re.compile(r"diplomagroep\s+staat\s+op", re.I),
    re.compile(r"^stellen\s+aan", re.I),
    re.compile(r"^onderwijs\s*\(", re.I),
    re.compile(r"^van de groep\s+waarin", re.I),
    re.compile(r"^diplomagroep\b", re.I),
    re.compile(r"^groep\s+\d+", re.I),
]

SECTION_HEADERS = {
    "mbo niveau 3": "mbo3",
    "mbo niveau 4": "mbo4",
    "hbo associate degree": "hbo",
    "hbo bachelor": "hbo",
    "hbo": "hbo",
}

# Patroon: eerste kwalificatiecode in de regel (A1 / A2 / B1 / B2)
CODE_RE = re.compile(r"\b(A[12]|B[12])\b")


def should_skip(line: str) -> bool:
    for pat in SKIP_PATTERNS:
        if pat.search(line):
            return True
    return False


def parse_kdv_bso(code_text: str):
    """
    Zet de ruwe code-tekst om naar (kdv_status, bso_status).

    CAO-codes:
      A1        → KDV direct,       BSO direct
      A2        → KDV proof,        BSO proof      (A dekt alles, maar met bewijs)
      A2 en B1  → KDV proof,        BSO direct     (B1 is beter dan A2 voor BSO)
      A2 en B2  → KDV proof,        BSO proof
      B1        → KDV niet,         BSO direct
      B2        → KDV niet,         BSO proof
    """
    codes = set(CODE_RE.findall(code_text))
    has_a1 = "A1" in codes
    has_a2 = "A2" in codes
    has_b1 = "B1" in codes
    has_b2 = "B2" in codes

    if has_a1:
        return "direct", "direct"
    if has_a2:
        kdv = "proof_required"
        bso = "direct" if has_b1 else "proof_required"
        return kdv, bso
    if has_b1:
        return "not_qualified", "direct"
    if has_b2:
        return "not_qualified", "proof_required"
    return "not_qualified", "not_qualified"


def is_continuation(line: str) -> bool:
    """Bepaalt of een regel een naamsafbreking is, geen nieuw diploma."""
    if not line:
        return False
    # Begint met kleine letter of verbindingswoord → afbreking
    if line[0].islower():
        return True
    for prefix in ("(", "en ", "of ", "en/", "of/", "- "):
        if line.startswith(prefix):
            return True
    return False


def extract_entries(text: str) -> list[dict]:
    """
    Parseert de platte tekst van de PDF naar een lijst van diploma-dicts.
    Elke dict bevat: name, level, kdv_status, bso_status, notes.

    Uitdaging: PDF-tabelregels kunnen afbreken na de kwalificatiecode.
    Voorbeeld:
        "Brancheopleiding Ervaren A1"   ← code op regel 1
        "Peuterspeelzaalleidster"        ← vervolg van de naam op regel 2
    We detecteren dit door te kijken of een regel zonder code direct na
    een entry staat EN niet begint als nieuw diploma (enkele hoofdletter-word,
    GEEN lange diplomatitel). Als de regel er als afbreking uitziet, voegen
    we hem toe aan het laatste entry.
    """
    entries: list[dict] = []
    current_level = "mbo3"
    pending_name_parts: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if should_skip(line):
            pending_name_parts = []   # reset ook buffer bij skip
            continue

        # Sectie-header detectie
        lower = line.lower()
        matched_section = None
        for header, level in SECTION_HEADERS.items():
            if lower.startswith(header):
                matched_section = level
                break
        if matched_section:
            current_level = matched_section
            pending_name_parts = []
            continue

        # Zoek eerste kwalificatiecode in de regel
        m = CODE_RE.search(line)
        if m:
            name_part = line[:m.start()].strip()
            code_text = line[m.start():].strip()

            parts = [p for p in pending_name_parts if p]
            if name_part:
                parts.append(name_part)
            full_name = " ".join(parts).strip()
            pending_name_parts = []

            if not full_name:
                continue

            kdv, bso = parse_kdv_bso(code_text)
            entries.append({
                "name": full_name,
                "level": current_level,
                "kdv_status": kdv,
                "bso_status": bso,
                "notes": f"CAO {code_text}",
                "crebo": "",
                "qualifying_roles": [],
                "qualifying_institution_types": [],
            })
        else:
            # Geen code in deze regel.
            if is_continuation(line):
                # Kleine-letter afbreking → voeg toe aan vorig entry (naam wrapping)
                if entries:
                    entries[-1]["name"] += " " + line
                # anders negeert: intro-resten
            elif entries and not pending_name_parts:
                # Regel zonder code direct ná een entry en zonder buffer:
                # dit is een naam-afbreking ná de code (tabel-artefact).
                # Voorbeeld: "Brancheopleiding Ervaren A1" → "Peuterspeelzaalleidster"
                entries[-1]["name"] += " " + line
            else:
                # Begin van een nieuwe naam (die nog geen code heeft gekregen)
                pending_name_parts.append(line)

    return entries


class Command(BaseCommand):
    help = "Importeert diplomalijst vanuit de officiële CAO Kinderopvang PDF"

    def add_arguments(self, parser):
        parser.add_argument("--url", default=CAO_PDF_URL, help="URL van de PDF")
        parser.add_argument("--file", default=None, help="Lokaal PDF-bestand (overschrijft --url)")
        parser.add_argument("--dry-run", action="store_true", help="Niet opslaan, alleen tellen")
        parser.add_argument("--clear", action="store_true", help="Verwijder bestaande PDF-diploma's eerst")

    def handle(self, *args, **options):
        try:
            import pdfplumber
        except ImportError:
            self.stderr.write("Installeer pdfplumber: pip install pdfplumber")
            return

        # ── Stap 1: PDF ophalen ───────────────────────────────────────────────
        if options["file"]:
            pdf_path = options["file"]
            self.stdout.write(f"PDF van schijf: {pdf_path}")
        else:
            url = options["url"]
            self.stdout.write(f"Downloaden: {url}")
            resp = requests.get(url, headers=DOWNLOAD_HEADERS, timeout=30)
            if resp.status_code != 200:
                self.stderr.write(f"Download mislukt: HTTP {resp.status_code}")
                return
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp.write(resp.content)
            tmp.flush()
            pdf_path = tmp.name
            self.stdout.write(f"Opgeslagen als: {pdf_path} ({len(resp.content) // 1024} KB)")

        # ── Stap 2: tekst extraheren ──────────────────────────────────────────
        full_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            self.stdout.write(f"PDF heeft {len(pdf.pages)} pagina's")
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    full_text += t + "\n"

        # ── Stap 3: parseren ──────────────────────────────────────────────────
        entries = extract_entries(full_text)
        self.stdout.write(f"Geparseerd: {len(entries)} diploma-entries")

        if options["dry_run"]:
            for e in entries[:20]:
                self.stdout.write(
                    f"  [{e['level']}] {e['name'][:60]:<60} "
                    f"KDV={e['kdv_status'][:6]}  BSO={e['bso_status'][:6]}"
                )
            self.stdout.write(f"  ... en nog {max(0, len(entries) - 20)} meer")
            return

        # ── Stap 4: opslaan ───────────────────────────────────────────────────
        if options["clear"]:
            deleted = Diploma.objects.filter(notes__startswith="CAO ").delete()[0]
            self.stdout.write(f"Verwijderd: {deleted} oud geïmporteerde diploma's")

        created = updated = skipped = 0
        for item in entries:
            if not item["name"]:
                skipped += 1
                continue
            obj, is_new = Diploma.objects.update_or_create(
                name=item["name"],
                level=item["level"],
                defaults={
                    "crebo": item.get("crebo", ""),
                    "kdv_status": item["kdv_status"],
                    "bso_status": item["bso_status"],
                    "qualifying_roles": item.get("qualifying_roles", []),
                    "qualifying_institution_types": item.get("qualifying_institution_types", []),
                    "notes": item["notes"],
                    "is_active": True,
                },
            )
            if is_new:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Klaar: {created} nieuw, {updated} bijgewerkt, {skipped} overgeslagen"
            )
        )
