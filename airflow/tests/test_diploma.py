"""
Unit tests voor scrapers/diploma.py

Test: parse_level, parse_status, parse_diploma_entries
Geen DB of netwerk vereist voor unit tests.
Integratie test (mark=integration): echte API call.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.diploma import parse_level, parse_status, parse_diploma_entries


# ── parse_level ───────────────────────────────────────────────────────────────

class TestParseLevel:
    def test_mbo3_dash(self):
        assert parse_level("mbo-3") == "mbo3"

    def test_mbo3_space(self):
        assert parse_level("MBO 3") == "mbo3"

    def test_mbo4(self):
        assert parse_level("mbo-4") == "mbo4"

    def test_mbo2(self):
        assert parse_level("mbo 2") == "mbo2"

    def test_wo_master(self):
        assert parse_level("Master Pedagogiek") == "wo"

    def test_wo_universitair(self):
        assert parse_level("Universitair") == "wo"

    def test_hbo_fallback(self):
        assert parse_level("HBO Pedagogiek") == "hbo"

    def test_empty_string(self):
        assert parse_level("") == "hbo"

    def test_case_insensitive(self):
        assert parse_level("MBO-3") == "mbo3"


# ── parse_status ──────────────────────────────────────────────────────────────

class TestParseStatus:
    def test_direct(self):
        assert parse_status("1") == "direct"

    def test_proof_required(self):
        assert parse_status("2") == "proof_required"

    def test_not_qualified(self):
        assert parse_status("0") == "not_qualified"

    def test_unknown_value(self):
        assert parse_status("99") == "not_qualified"

    def test_empty(self):
        assert parse_status("") == "not_qualified"


# ── parse_diploma_entries ─────────────────────────────────────────────────────

class TestParseDiplomaEntries:

    def make_item(self, title, nid="1", dagopvang="1", bso="2"):
        return {
            "title": title,
            "nid": nid,
            "field_dagopvang": dagopvang,
            "field_buitenschoolse_opvang": bso,
        }

    def test_basic_entry(self):
        items = [self.make_item("SPW (MBO-3)")]
        entries = parse_diploma_entries(items)
        assert len(entries) == 1
        e = entries[0]
        assert e["name"] == "SPW"
        assert e["level"] == "mbo3"
        assert e["kdv_status"] == "direct"
        assert e["bso_status"] == "proof_required"

    def test_strips_level_from_name(self):
        items = [self.make_item("Pedagogisch Werk (MBO-4)")]
        entries = parse_diploma_entries(items)
        assert entries[0]["name"] == "Pedagogisch Werk"
        assert entries[0]["level"] == "mbo4"

    def test_skips_empty_title(self):
        items = [{"title": "", "nid": "1", "field_dagopvang": "1", "field_buitenschoolse_opvang": "1"}]
        entries = parse_diploma_entries(items)
        assert entries == []

    def test_multiple_entries(self):
        items = [
            self.make_item("SPW (MBO-3)", nid="1"),
            self.make_item("Pedagogisch Werk (MBO-4)", nid="2", dagopvang="0", bso="0"),
        ]
        entries = parse_diploma_entries(items)
        assert len(entries) == 2
        assert entries[0]["name"] == "SPW"
        assert entries[1]["kdv_status"] == "not_qualified"

    def test_nid_in_notes(self):
        items = [self.make_item("SPW (MBO-3)", nid="42")]
        entries = parse_diploma_entries(items)
        assert "42" in entries[0]["notes"]

    def test_no_level_in_title_defaults_hbo(self):
        items = [self.make_item("Bachelor Pedagogiek")]
        entries = parse_diploma_entries(items)
        assert entries[0]["level"] == "hbo"
        assert entries[0]["name"] == "Bachelor Pedagogiek"

    def test_empty_list(self):
        assert parse_diploma_entries([]) == []

    def test_missing_fields_default_not_qualified(self):
        items = [{"title": "SPW (MBO-3)", "nid": "1"}]
        entries = parse_diploma_entries(items)
        assert entries[0]["kdv_status"] == "not_qualified"
        assert entries[0]["bso_status"] == "not_qualified"


# ── Integratie test (echte API, vereist netwerk) ──────────────────────────────

@pytest.mark.integration
class TestDiplomaLive:
    """Uitvoeren met: pytest -m integration tests/test_diploma.py -v -s"""

    def test_api_returns_diplomas(self):
        import requests
        from scrapers.diploma import API_URL, HEADERS

        resp = requests.get(API_URL, headers=HEADERS, timeout=30)
        assert resp.status_code == 200

        data = resp.json()
        assert data.get("success") is True
        assert "diplomas" in data
        assert len(data["diplomas"]) > 100, "Verwacht >100 diploma's van API"

        entries = parse_diploma_entries(data["diplomas"])
        print(f"\n[INFO] {len(entries)} diploma's geparseerd")
        print(f"[INFO] Eerste: {entries[0]}")

        assert len(entries) > 100
        e = entries[0]
        assert e["name"]
        assert e["level"] in ("mbo2", "mbo3", "mbo4", "hbo", "wo")
        assert e["kdv_status"] in ("direct", "proof_required", "not_qualified")
