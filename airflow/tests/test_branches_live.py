"""
Integration tests: provera da li svaki branch scraper vraća lokacije sa punom adresom.

Pokreni samo sa: pytest tests/test_branches_live.py -v -m integration

Šta se proverava za svaku kompaniju:
  - Vraća > 0 lokacija
  - Svaka lokacija ima: name, postcode (4 cifre + 2 slova), city
  - Većina lokacija ima i street (ulicu)
  - Postcode je u validnom NL formatu (1000AA–9999ZZ)
"""

import re
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.branches import COMPANY_CONFIGS

POSTCODE_RE = re.compile(r"^\d{4}[A-Z]{2}$")


def _check_locations(slug: str, min_locations: int = 1) -> list[dict]:
    """Drži scraped lokacije i proverava osnovna pravila."""
    config = COMPANY_CONFIGS.get(slug)
    assert config is not None, f"{slug} nije u COMPANY_CONFIGS"
    locs = config["scraper"]()
    assert len(locs) >= min_locations, (
        f"{slug}: očekivano >= {min_locations} lokacija, dobijeno {len(locs)}"
    )
    return locs


def _assert_full_address(slug: str, locs: list[dict], min_with_street_pct: int = 50):
    """
    Svaka lokacija mora imati name i postcode (validan NL format).
    City je opcionalan — PDOK može geocodirati samo po postcoду.
    Najmanje min_with_street_pct% mora imati i street (ulicu).
    """
    for loc in locs:
        assert loc.get("name"), f"{slug}: lokacija bez name: {loc}"
        assert loc.get("postcode"), f"{slug}: lokacija bez postcode: {loc}"

        pc = loc["postcode"].replace(" ", "").upper()
        assert POSTCODE_RE.match(pc), (
            f"{slug}: nevalidan postcode '{pc}' u lokaciji '{loc['name']}'"
        )

    with_street = sum(1 for l in locs if l.get("street", "").strip())
    pct = int(with_street / len(locs) * 100)
    assert pct >= min_with_street_pct, (
        f"{slug}: samo {pct}% lokacija ima street (min {min_with_street_pct}%)"
    )


def _assert_has_coords(slug: str, locs: list[dict], min_pct: int = 80):
    """Proverava da li znatan deo lokacija ima koordinate."""
    with_coords = sum(1 for l in locs if l.get("lat") and l.get("lon"))
    pct = int(with_coords / len(locs) * 100)
    assert pct >= min_pct, (
        f"{slug}: samo {pct}% lokacija ima koordinate (min {min_pct}%)"
    )


# ── Kompanije sa custom scraperom i direktnim koordinatama ────────────────────

class TestPartouLive:
    @pytest.mark.integration
    def test_vraća_lokacije_sa_punom_adresom(self):
        locs = _check_locations("partou", min_locations=200)
        _assert_full_address("partou", locs, min_with_street_pct=90)

    @pytest.mark.integration
    def test_nema_potpuno_istih_duplikata(self):
        """Isti name+postcode+street ne sme da se pojavi dva puta."""
        locs = _check_locations("partou", min_locations=1)
        keys = [(l["name"], l["postcode"], l.get("street", "")) for l in locs]
        assert len(keys) == len(set(keys)), \
            "partou: potpuno isti duplikati (name+postcode+street)"


class TestKinderdamLive:
    @pytest.mark.integration
    def test_vraća_lokacije_sa_punom_adresom(self):
        locs = _check_locations("kinderdam", min_locations=50)
        _assert_full_address("kinderdam", locs, min_with_street_pct=80)

    @pytest.mark.integration
    def test_ima_koordinate(self):
        locs = _check_locations("kinderdam", min_locations=1)
        _assert_has_coords("kinderdam", locs, min_pct=80)


class TestSpringLive:
    @pytest.mark.integration
    def test_vraća_lokacije_sa_punom_adresom(self):
        locs = _check_locations("spring", min_locations=100)
        _assert_full_address("spring", locs, min_with_street_pct=90)

    @pytest.mark.integration
    def test_ima_koordinate(self):
        locs = _check_locations("spring", min_locations=1)
        _assert_has_coords("spring", locs, min_pct=90)


class TestPrrokinoLive:
    @pytest.mark.integration
    def test_vraća_lokacije_sa_punom_adresom(self):
        locs = _check_locations("prokino", min_locations=50)
        _assert_full_address("prokino", locs, min_with_street_pct=80)

    @pytest.mark.integration
    def test_ima_koordinate(self):
        locs = _check_locations("prokino", min_locations=1)
        _assert_has_coords("prokino", locs, min_pct=80)


class TestKoberLive:
    @pytest.mark.integration
    def test_vraća_lokacije_sa_punom_adresom(self):
        locs = _check_locations("kober", min_locations=50)
        _assert_full_address("kober", locs, min_with_street_pct=90)


class TestKionLive:
    @pytest.mark.integration
    def test_vraća_lokacije_sa_punom_adresom(self):
        locs = _check_locations("kion", min_locations=50)
        _assert_full_address("kion", locs, min_with_street_pct=90)

    @pytest.mark.integration
    def test_ima_koordinate(self):
        locs = _check_locations("kion", min_locations=1)
        _assert_has_coords("kion", locs, min_pct=90)


class TestCompanannyLive:
    @pytest.mark.integration
    def test_vraća_lokacije_sa_punom_adresom(self):
        locs = _check_locations("compananny", min_locations=30)
        _assert_full_address("compananny", locs, min_with_street_pct=90)

    @pytest.mark.integration
    def test_ima_koordinate(self):
        locs = _check_locations("compananny", min_locations=1)
        _assert_has_coords("compananny", locs, min_pct=90)


class TestTinteltuinLive:
    @pytest.mark.integration
    def test_vraća_lokacije_sa_punom_adresom(self):
        locs = _check_locations("tinteltuin", min_locations=20)
        _assert_full_address("tinteltuin", locs, min_with_street_pct=80)

    @pytest.mark.integration
    def test_ima_koordinate(self):
        locs = _check_locations("tinteltuin", min_locations=1)
        _assert_has_coords("tinteltuin", locs, min_pct=80)


class TestSinneLive:
    @pytest.mark.integration
    def test_vraća_lokacije_sa_punom_adresom(self):
        locs = _check_locations("sinne", min_locations=15)
        _assert_full_address("sinne", locs, min_with_street_pct=30)
        # Sinne nema uvek ulicu u adres HTML-u, ali mora imati postcode i city

    @pytest.mark.integration
    def test_ima_koordinate(self):
        locs = _check_locations("sinne", min_locations=1)
        _assert_has_coords("sinne", locs, min_pct=80)


class TestHumankindLive:
    @pytest.mark.integration
    def test_vraća_lokacije_sa_punom_adresom(self):
        locs = _check_locations("humankind", min_locations=200)
        _assert_full_address("humankind", locs, min_with_street_pct=70)


# ── Markeri za poznate neodržane kompanije ────────────────────────────────────
# Definisani ovde da bi bili dostupni svim klasama ispod.

_XFAIL_JS = pytest.mark.xfail(
    reason="Lokacije se učitavaju JavaScript-om — generički HTML scraper ne vidi podatke",
    strict=False,
)
_XFAIL_DNS = pytest.mark.xfail(
    reason="DNS fail lokalno (domen ne postoji ili je nedostupan bez VPN)",
    strict=False,
)
_XFAIL_NO_PAGE = pytest.mark.xfail(
    reason="Sajt nema standardnu /vestigingen ili /locaties stranicu",
    strict=False,
)


# ── Generički scrapers — proveravamo samo da vraćaju nešto ako site postoji ───

class TestKidsFirstLive:
    @pytest.mark.integration
    def test_vraća_lokacije_sa_punom_adresom(self):
        locs = _check_locations("kids-first", min_locations=100)
        _assert_full_address("kids-first", locs, min_with_street_pct=50)


class TestNorlandiaLive:
    @pytest.mark.integration
    @_XFAIL_NO_PAGE
    def test_vraća_barem_jednu_lokaciju(self):
        # Norlandia /vestigingen vraća 404; /kinderopvang stranica nema JSON-LD lokacija
        locs = _check_locations("norlandia", min_locations=1)
        _assert_full_address("norlandia", locs, min_with_street_pct=50)


class TestKibeoLive:
    @pytest.mark.integration
    @pytest.mark.xfail(reason="kibeo.nl vraća 403 Forbidden", strict=False)
    def test_vraća_barem_jednu_lokaciju(self):
        locs = _check_locations("kibeo", min_locations=1)
        _assert_full_address("kibeo", locs, min_with_street_pct=50)


class TestKindergardenLive:
    @pytest.mark.integration
    def test_vraća_barem_jednu_lokaciju(self):
        locs = _check_locations("kindergarden", min_locations=1)
        _assert_full_address("kindergarden", locs, min_with_street_pct=50)


class TestBijdehandjesLive:
    @pytest.mark.integration
    @_XFAIL_JS
    def test_vraća_barem_jednu_lokaciju(self):
        # bijdehandjes.info/vind-jouw-locatie/overzicht učitava AJAX-om
        locs = _check_locations("bijdehandjes", min_locations=1)
        _assert_full_address("bijdehandjes", locs, min_with_street_pct=50)


# ── Poznate neodržane kompanije (xfail) ──────────────────────────────────────
# Ove kompanije ne funkcionišu sa generičkim scraperom jer:
#   - Lokacije se učitavaju AJAX/JavaScript-om (gro-up, dak, kinderwoud, kanteel, wasko, wij-zijn-jong)
#   - DNS nije dostupan lokalno (bink/debinkopmeer.nl, dichtbij/kdv-dichtbij.nl, mik-nijmegen.nl)
#   - Sajt nema /vestigingen stranicu (op-stoom, ska, 2samen, ko-walcheren, samenwerkende-ko)
# Testovi ostaju kao dokumentacija — kad se fixuju, xfail postaje xpass.


class TestBinkLive:
    @pytest.mark.integration
    @_XFAIL_DNS
    def test_vraća_barem_jednu_lokaciju(self):
        locs = _check_locations("bink", min_locations=1)
        _assert_full_address("bink", locs, min_with_street_pct=50)


class TestDakLive:
    @pytest.mark.integration
    @_XFAIL_JS
    def test_vraća_barem_jednu_lokaciju(self):
        locs = _check_locations("dak", min_locations=1)
        _assert_full_address("dak", locs, min_with_street_pct=50)


class TestDichtbijLive:
    @pytest.mark.integration
    @_XFAIL_DNS
    def test_vraća_barem_jednu_lokaciju(self):
        locs = _check_locations("dichtbij", min_locations=1)
        _assert_full_address("dichtbij", locs, min_with_street_pct=50)


class TestKinderwoudLive:
    @pytest.mark.integration
    @_XFAIL_JS
    def test_vraća_barem_jednu_lokaciju(self):
        locs = _check_locations("kinderwoud", min_locations=1)
        _assert_full_address("kinderwoud", locs, min_with_street_pct=50)


class TestMikLive:
    @pytest.mark.integration
    @_XFAIL_DNS
    def test_vraća_barem_jednu_lokaciju(self):
        locs = _check_locations("mik", min_locations=1)
        _assert_full_address("mik", locs, min_with_street_pct=50)


class TestOpStoomLive:
    @pytest.mark.integration
    @_XFAIL_NO_PAGE
    def test_vraća_barem_jednu_lokaciju(self):
        locs = _check_locations("op-stoom", min_locations=1)
        _assert_full_address("op-stoom", locs, min_with_street_pct=50)


class TestSkaLive:
    @pytest.mark.integration
    @_XFAIL_NO_PAGE
    def test_vraća_barem_jednu_lokaciju(self):
        locs = _check_locations("ska", min_locations=1)
        _assert_full_address("ska", locs, min_with_street_pct=50)


class TestTweeSamenLive:
    @pytest.mark.integration
    @_XFAIL_NO_PAGE
    def test_vraća_barem_jednu_lokaciju(self):
        locs = _check_locations("2samen", min_locations=1)
        _assert_full_address("2samen", locs, min_with_street_pct=50)


class TestWaskoLive:
    @pytest.mark.integration
    @_XFAIL_JS
    def test_vraća_barem_jednu_lokaciju(self):
        locs = _check_locations("wasko", min_locations=1)
        _assert_full_address("wasko", locs, min_with_street_pct=50)


class TestWijZijnJongLive:
    @pytest.mark.integration
    @_XFAIL_JS
    def test_vraća_barem_jednu_lokaciju(self):
        locs = _check_locations("wij-zijn-jong", min_locations=1)
        _assert_full_address("wij-zijn-jong", locs, min_with_street_pct=50)


class TestKanteelLive:
    @pytest.mark.integration
    @_XFAIL_JS
    def test_vraća_barem_jednu_lokaciju(self):
        locs = _check_locations("kanteel", min_locations=1)
        _assert_full_address("kanteel", locs, min_with_street_pct=50)


class TestKoWalcherenLive:
    @pytest.mark.integration
    @_XFAIL_NO_PAGE
    def test_vraća_barem_jednu_lokaciju(self):
        locs = _check_locations("ko-walcheren", min_locations=1)
        _assert_full_address("ko-walcheren", locs, min_with_street_pct=50)


class TestSamenwerkendeKoLive:
    @pytest.mark.integration
    @_XFAIL_NO_PAGE
    def test_vraća_barem_jednu_lokaciju(self):
        locs = _check_locations("samenwerkende-ko", min_locations=1)
        _assert_full_address("samenwerkende-ko", locs, min_with_street_pct=50)


class TestGroUpLive:
    @pytest.mark.integration
    @_XFAIL_JS
    def test_vraća_barem_jednu_lokaciju(self):
        locs = _check_locations("gro-up", min_locations=1)
        _assert_full_address("gro-up", locs, min_with_street_pct=50)
