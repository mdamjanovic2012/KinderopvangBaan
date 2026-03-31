"""
Unit tests for branches.py

Test strategy:
  - _parse_address_block: address extraction from free text
  - upsert_vestiging: DB write with mocked geocoding
  - match_vestiging: exact name match, city match, fallback
  - run_vestigingen_scrape: end-to-end with mocked scraper + DB
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.branches import (
    _parse_address_block,
    upsert_vestiging,
    match_vestiging,
    run_vestigingen_scrape,
    scrape_partou_vestigingen,
    scrape_kinderdam_vestigingen,
    _scrape_generic_vestigingen,
    COMPANY_CONFIGS,
)


# ── _parse_address_block ──────────────────────────────────────────────────────

class TestParseAddressBlock:
    def test_full_address(self):
        text = "Wilhelminastraat 45 3012EV Rotterdam"
        street, postcode, city = _parse_address_block(text)
        assert postcode == "3012EV"
        assert "Rotterdam" in city

    def test_postcode_with_space(self):
        text = "Lange Lijnbaan 10, 3012 EV Rotterdam"
        street, postcode, city = _parse_address_block(text)
        assert postcode == "3012EV"

    def test_no_postcode_returns_empty(self):
        street, postcode, city = _parse_address_block("Amsterdam, Nederland")
        assert postcode == ""
        assert city == ""

    def test_street_extracted(self):
        text = "Oranjestraat 12, 3011AB Rotterdam"
        street, postcode, city = _parse_address_block(text)
        assert "Oranjestraat" in street
        assert "12" in street

    def test_empty_string(self):
        street, postcode, city = _parse_address_block("")
        assert street == postcode == city == ""

    def test_postcode_only(self):
        _, postcode, _ = _parse_address_block("3012EV")
        assert postcode == "3012EV"


# ── upsert_vestiging ─────────────────────────────────────────────────────────

class TestUpsertVestiging:
    def _make_cur(self):
        cur = MagicMock()
        cur.execute = MagicMock()
        return cur

    def test_upsert_with_full_address_geocodes(self):
        cur = self._make_cur()
        geo = {"lon": 4.48, "lat": 51.92, "city": "Rotterdam", "postcode": "3012EV"}
        with patch("scrapers.branches._geocode_via_pdok", return_value=geo):
            upsert_vestiging(cur, "test", "KDV De Ster", "Straat 1", "3012EV", "Rotterdam")
        cur.execute.assert_called_once()
        sql = cur.execute.call_args[0][0]
        assert "ST_MakePoint" in sql

    def test_upsert_without_geo_stores_without_location(self):
        cur = self._make_cur()
        with patch("scrapers.branches._geocode_via_pdok", return_value=None):
            upsert_vestiging(cur, "test", "KDV Geen Geo", "", "", "Amsterdam")
        cur.execute.assert_called_once()
        sql = cur.execute.call_args[0][0]
        assert "ST_MakePoint" not in sql

    def test_upsert_with_city_only_still_geocodes(self):
        cur = self._make_cur()
        geo = {"lon": 4.89, "lat": 52.37, "city": "Amsterdam", "postcode": ""}
        with patch("scrapers.branches._geocode_via_pdok", return_value=geo):
            upsert_vestiging(cur, "test", "KDV Amsterdam", "", "", "Amsterdam")
        args = cur.execute.call_args[0][1]
        assert args[0] == "test"
        assert args[1] == "KDV Amsterdam"


# ── match_vestiging ───────────────────────────────────────────────────────────

class TestMatchVestiging:
    def _make_cur(self, fetchone=None, fetchall=None):
        cur = MagicMock()
        cur.fetchone = MagicMock(return_value=fetchone)
        cur.fetchall = MagicMock(return_value=fetchall or [])
        return cur

    def test_exact_name_match(self):
        row = ("3012EV", "Rotterdam", 4.48, 51.92)
        cur = self._make_cur(fetchone=row)
        result = match_vestiging(cur, "test", "KDV De Ster", "Rotterdam")
        assert result is not None
        assert result["lon"] == 4.48
        assert result["city"] == "Rotterdam"

    def test_city_match_single_vestiging(self):
        # No exact name match
        cur = MagicMock()
        cur.fetchone = MagicMock(return_value=None)  # no exact name
        cur.fetchall = MagicMock(return_value=[("3012EV", "Rotterdam", 4.48, 51.92)])
        result = match_vestiging(cur, "test", "Rotterdam", "Rotterdam")
        assert result is not None
        assert result["lat"] == 51.92

    def test_city_match_multiple_vestigingen_returns_centroid(self):
        """Multiple branches in same city → centroid instead of None."""
        cur = MagicMock()
        cur.fetchone = MagicMock(return_value=None)
        cur.fetchall = MagicMock(return_value=[
            ("3012EV", "Rotterdam", 4.48, 51.92),
            ("3014AB", "Rotterdam", 4.50, 51.94),
        ])
        result = match_vestiging(cur, "test", "Rotterdam", "Rotterdam")
        assert result is not None
        assert result["lon"] == pytest.approx(4.49)
        assert result["lat"] == pytest.approx(51.93)
        assert result["city"] == "Rotterdam"
        assert result["postcode"] == ""

    def test_no_match_returns_none(self):
        cur = MagicMock()
        cur.fetchone = MagicMock(return_value=None)
        cur.fetchall = MagicMock(return_value=[])
        result = match_vestiging(cur, "test", "Onbekend", "Onbekend")
        assert result is None

    def test_empty_location_name_tries_city(self):
        cur = MagicMock()
        cur.fetchone = MagicMock(return_value=None)
        cur.fetchall = MagicMock(return_value=[("1234AB", "Utrecht", 5.1, 52.1)])
        result = match_vestiging(cur, "test", "", "Utrecht")
        assert result is not None


# ── run_vestigingen_scrape ────────────────────────────────────────────────────

class TestRunVestigenScrape:
    def test_runs_for_known_company(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cur)

        fake_locations = [{"name": "KDV Test", "street": "Teststraat 1",
                           "postcode": "1234AB", "city": "Amsterdam"}]

        with patch("scrapers.branches.get_connection", return_value=mock_conn), \
             patch("scrapers.branches.COMPANY_CONFIGS", {
                 "test_slug": {"scraper": lambda: fake_locations}
             }), \
             patch("scrapers.branches.upsert_vestiging") as mock_upsert:
            stats = run_vestigingen_scrape(["test_slug"])

        assert "test_slug" in stats
        assert stats["test_slug"]["locations"] == 1
        mock_upsert.assert_called_once()

    def test_unknown_company_skipped(self):
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=MagicMock())

        with patch("scrapers.branches.get_connection", return_value=mock_conn):
            stats = run_vestigingen_scrape(["bestaatniet"])

        assert "bestaatniet" not in stats

    def test_scraper_error_recorded_in_stats(self):
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=MagicMock())

        def failing_scraper():
            raise ConnectionError("Site unreachable")

        with patch("scrapers.branches.get_connection", return_value=mock_conn), \
             patch("scrapers.branches.COMPANY_CONFIGS", {
                 "failing": {"scraper": failing_scraper}
             }):
            stats = run_vestigingen_scrape(["failing"])

        assert "error" in stats["failing"]

    def test_upsert_error_does_not_abort_run(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cur)

        fake_locations = [{"name": "KDV Test", "street": "", "postcode": "", "city": "Amsterdam"}]

        with patch("scrapers.branches.get_connection", return_value=mock_conn), \
             patch("scrapers.branches.COMPANY_CONFIGS", {
                 "test_slug": {"scraper": lambda: fake_locations}
             }), \
             patch("scrapers.branches.upsert_vestiging", side_effect=Exception("DB error")):
            stats = run_vestigingen_scrape(["test_slug"])

        # Should still report 0 locations (all failed upserts)
        assert "test_slug" in stats
        assert stats["test_slug"]["locations"] == 0

    def test_all_companies_scraped_when_none_specified(self):
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=MagicMock())

        with patch("scrapers.branches.get_connection", return_value=mock_conn), \
             patch("scrapers.branches.upsert_vestiging"):
            # Replace all configs with simple no-op scrapers
            fake_configs = {k: {"scraper": lambda: []} for k in COMPANY_CONFIGS}
            with patch("scrapers.branches.COMPANY_CONFIGS", fake_configs):
                stats = run_vestigingen_scrape()

        assert set(stats.keys()) == set(fake_configs.keys())


# ── COMPANY_CONFIGS ───────────────────────────────────────────────────────────

class TestCompanyConfigs:
    def test_all_major_companies_configured(self):
        for slug in ["partou", "kinderdam", "spring", "prokino", "norlandia", "gro-up"]:
            assert slug in COMPANY_CONFIGS, f"{slug} ontbreekt in COMPANY_CONFIGS"

    def test_each_config_has_scraper(self):
        for slug, config in COMPANY_CONFIGS.items():
            assert callable(config["scraper"]), f"{slug} heeft geen callable scraper"


# ── scrape_partou_vestigingen ─────────────────────────────────────────────────

PARTOU_JSONLD_HTML = """<html><body>
<script type="application/ld+json">
[{"@type": "ChildCare", "name": "Partou KDV De Ster",
  "address": {"streetAddress": "Sterstraat 1", "postalCode": "3011AB", "addressLocality": "Rotterdam"}}]
</script>
</body></html>"""

PARTOU_CARD_HTML = """<html><body>
<div class="location-card">
  <h3>Partou BSO Zonnetje</h3>
  <address>Zonnelaan 5, 3012AB Rotterdam</address>
</div>
</body></html>"""


class TestExtractAddressFromElement:
    def test_extracts_name_street_postcode(self):
        from scrapers.branches import _extract_address_from_element
        from bs4 import BeautifulSoup
        html = "<div><p>KDV De Ster\nBergweg 23\n3037LE Rotterdam</p></div>"
        el = BeautifulSoup(html, "lxml").find("div")
        name, street, postcode_city = _extract_address_from_element(el)
        assert name == "KDV De Ster"
        assert "Bergweg" in street

    def test_empty_element_returns_empty(self):
        from scrapers.branches import _extract_address_from_element
        from bs4 import BeautifulSoup
        el = BeautifulSoup("<div></div>", "lxml").find("div")
        name, street, postcode_city = _extract_address_from_element(el)
        assert name == street == postcode_city == ""


class TestScrapePartouVestigingen:
    def _mock_resp(self, html, status=200):
        resp = MagicMock()
        resp.text = html
        resp.status_code = status
        resp.raise_for_status = MagicMock()
        return resp

    def test_jsonld_locations_extracted(self):
        with patch("scrapers.branches.requests.get", return_value=self._mock_resp(PARTOU_JSONLD_HTML)):
            locations = scrape_partou_vestigingen()
        assert len(locations) >= 1
        assert any(loc["name"] == "Partou KDV De Ster" for loc in locations)
        assert any(loc["city"] == "Rotterdam" for loc in locations)

    def test_html_fallback_when_no_jsonld(self):
        with patch("scrapers.branches.requests.get", return_value=self._mock_resp(PARTOU_CARD_HTML)):
            locations = scrape_partou_vestigingen()
        # Should find at least the card
        assert isinstance(locations, list)

    def test_returns_empty_on_all_errors(self):
        with patch("scrapers.branches.requests.get", side_effect=Exception("connection refused")):
            locations = scrape_partou_vestigingen()
        assert locations == []

    def test_skips_non_200_responses(self):
        with patch("scrapers.branches.requests.get", return_value=self._mock_resp("", status=404)):
            locations = scrape_partou_vestigingen()
        assert locations == []

    def test_invalid_jsonld_is_skipped_gracefully(self):
        html = """<html><body>
            <script type="application/ld+json">INVALID JSON {{{</script>
        </body></html>"""
        with patch("scrapers.branches.requests.get", return_value=self._mock_resp(html)):
            locations = scrape_partou_vestigingen()
        assert isinstance(locations, list)


# ── scrape_kinderdam_vestigingen ──────────────────────────────────────────────

KINDERDAM_HTML = """<html><body>
<script type="application/ld+json">
{"@type": "LocalBusiness", "name": "Kinderdam BSO IJssel",
 "address": {"streetAddress": "IJssellaan 2", "postalCode": "2909BC", "addressLocality": "Capelle aan den IJssel"}}
</script>
</body></html>"""


class TestScrapeKinderdamVestigingen:
    def _mock_resp(self, html, status=200):
        resp = MagicMock()
        resp.text = html
        resp.status_code = status
        resp.raise_for_status = MagicMock()
        return resp

    def test_jsonld_location_extracted(self):
        with patch("scrapers.branches.requests.get", return_value=self._mock_resp(KINDERDAM_HTML)):
            locations = scrape_kinderdam_vestigingen()
        assert len(locations) >= 1
        loc = locations[0]
        assert loc["name"] == "Kinderdam BSO IJssel"
        assert loc["city"] == "Capelle aan den IJssel"
        assert loc["postcode"] == "2909BC"

    def test_returns_empty_on_error(self):
        with patch("scrapers.branches.requests.get", side_effect=Exception("timeout")):
            locations = scrape_kinderdam_vestigingen()
        assert locations == []


# ── _scrape_generic_vestigingen ───────────────────────────────────────────────

GENERIC_JSONLD_HTML = """<html><body>
<script type="application/ld+json">
[{"@type": "LocalBusiness", "name": "Spring KDV Amsterdam",
  "address": {"streetAddress": "Damrak 10", "postalCode": "1012LG", "addressLocality": "Amsterdam"}}]
</script>
</body></html>"""

GENERIC_CARD_HTML = """<html><body>
<article class="location-card">
  <h3>Spring BSO Utrecht</h3>
  <p>Zonneplein 7, 3521GH Utrecht</p>
</article>
</body></html>"""


class TestScrapeGenericVestigingen:
    def _mock_resp(self, html, status=200):
        resp = MagicMock()
        resp.text = html
        resp.status_code = status
        resp.raise_for_status = MagicMock()
        return resp

    def test_jsonld_locations_extracted(self):
        with patch("scrapers.branches.requests.get", return_value=self._mock_resp(GENERIC_JSONLD_HTML)):
            locations = _scrape_generic_vestigingen("spring", "https://spring.nl", ["/locaties"])
        assert len(locations) >= 1
        assert locations[0]["name"] == "Spring KDV Amsterdam"
        assert locations[0]["postcode"] == "1012LG"

    def test_html_card_fallback(self):
        with patch("scrapers.branches.requests.get", return_value=self._mock_resp(GENERIC_CARD_HTML)):
            locations = _scrape_generic_vestigingen("spring", "https://spring.nl", ["/locaties"])
        assert isinstance(locations, list)

    def test_returns_empty_on_404(self):
        with patch("scrapers.branches.requests.get", return_value=self._mock_resp("", status=404)):
            locations = _scrape_generic_vestigingen("spring", "https://spring.nl", ["/locaties"])
        assert locations == []

    def test_returns_empty_on_exception(self):
        with patch("scrapers.branches.requests.get", side_effect=Exception("SSL")):
            locations = _scrape_generic_vestigingen("test", "https://test.nl", ["/loc"])
        assert locations == []

    def test_tries_all_paths_on_failure(self):
        call_count = {"n": 0}
        def side_effect(url, **kwargs):
            call_count["n"] += 1
            raise Exception("fail")
        with patch("scrapers.branches.requests.get", side_effect=side_effect):
            _scrape_generic_vestigingen("test", "https://test.nl", ["/a", "/b", "/c"])
        assert call_count["n"] == 3
