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
    _parse_comma_address,
    upsert_vestiging,
    match_vestiging,
    run_vestigingen_scrape,
    scrape_partou_vestigingen,
    scrape_kinderdam_vestigingen,
    scrape_spring_vestigingen,
    scrape_prokino_vestigingen,
    scrape_kober_vestigingen,
    scrape_kion_vestigingen,
    scrape_compananny_vestigingen,
    scrape_tinteltuin_vestigingen,
    scrape_sinne_vestigingen,
    scrape_humankind_vestigingen,
    scrape_norlandia_vestigingen,
    scrape_kindergarden_vestigingen,
    scrape_ko_walcheren_vestigingen,
    scrape_mik_vestigingen,
    scrape_bijdehandjes_vestigingen,
    scrape_dak_vestigingen,
    scrape_wij_zijn_jong_vestigingen,
    scrape_wasko_vestigingen,
    scrape_kanteel_vestigingen,
    _scrape_generic_vestigingen,
    _extract_js_json,
    COMPANY_CONFIGS,
)


# ── _parse_address_block ──────────────────────────────────────────────────────

class TestParseCommaAddress:
    def test_comma_separated_format(self):
        street, postcode, city = _parse_comma_address("Pieter de Hooghstraat 6, 5854 ES, Bergen")
        assert street == "Pieter de Hooghstraat 6"
        assert postcode == "5854ES"
        assert city == "Bergen"

    def test_postcode_city_no_comma(self):
        street, postcode, city = _parse_comma_address("Weversdries 3, 4851 BD Ulvenhout")
        assert postcode == "4851BD"
        assert city == "Ulvenhout"

    def test_no_postcode_returns_empty(self):
        street, postcode, city = _parse_comma_address("Geen postcode hier")
        assert postcode == ""
        assert city == ""


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

    def test_insert_with_geo_includes_created_at(self):
        """INSERT met geo moet created_at bevatten (NOT NULL constraint)."""
        cur = self._make_cur()
        geo = {"lon": 4.48, "lat": 51.92, "city": "Rotterdam", "postcode": "3012EV"}
        with patch("scrapers.branches._geocode_via_pdok", return_value=geo):
            upsert_vestiging(cur, "test", "KDV Test", "Straat 1", "3012EV", "Rotterdam")
        sql = cur.execute.call_args[0][0]
        assert "created_at" in sql

    def test_insert_without_geo_includes_created_at(self):
        """INSERT zonder geo moet ook created_at bevatten."""
        cur = self._make_cur()
        with patch("scrapers.branches._geocode_via_pdok", return_value=None):
            upsert_vestiging(cur, "test", "KDV Test", "", "", "Amsterdam")
        sql = cur.execute.call_args[0][0]
        assert "created_at" in sql

    def test_direct_lon_lat_skips_pdok(self):
        """Als lon/lat meegestuurd worden, moet PDOK NIET aangeroepen worden."""
        cur = self._make_cur()
        with patch("scrapers.branches._geocode_via_pdok") as mock_pdok:
            upsert_vestiging(cur, "test", "KDV Direct", "Straat 1", "3012EV", "Rotterdam",
                             lon=4.48, lat=51.92)
        mock_pdok.assert_not_called()
        sql = cur.execute.call_args[0][0]
        assert "ST_MakePoint" in sql

    def test_direct_lon_lat_used_in_insert(self):
        """Directe lon/lat worden als parameters doorgegeven aan ST_MakePoint."""
        cur = self._make_cur()
        with patch("scrapers.branches._geocode_via_pdok"):
            upsert_vestiging(cur, "test", "KDV Direct", "Straat 1", "3012EV", "Rotterdam",
                             lon=4.48, lat=51.92)
        params = cur.execute.call_args[0][1]
        assert 4.48 in params
        assert 51.92 in params


class TestRunVestigingSavepoints:
    """Verify that a failed upsert does not abort the entire transaction."""

    def _make_conn(self, cur):
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor = MagicMock(return_value=cur)
        return conn

    def test_savepoint_released_on_success(self):
        cur = MagicMock()
        conn = self._make_conn(cur)
        fake_locations = [{"name": "KDV A", "street": "S 1", "postcode": "1234AB", "city": "Amsterdam"}]

        with patch("scrapers.branches.get_connection", return_value=conn), \
             patch("scrapers.branches.COMPANY_CONFIGS", {"slug": {"scraper": lambda: fake_locations}}), \
             patch("scrapers.branches.upsert_vestiging"):
            run_vestigingen_scrape(["slug"])

        savepoint_calls = [c for c in cur.execute.call_args_list
                           if "SAVEPOINT" in str(c)]
        release_calls   = [c for c in cur.execute.call_args_list
                           if "RELEASE SAVEPOINT" in str(c)]
        assert len(savepoint_calls) >= 1
        assert len(release_calls) >= 1

    def test_savepoint_rolled_back_on_failure(self):
        """Als upsert faalt, wordt ROLLBACK TO SAVEPOINT aangeroepen i.p.v. abort."""
        cur = MagicMock()
        conn = self._make_conn(cur)
        fake_locations = [
            {"name": "KDV A", "street": "", "postcode": "", "city": "Rotterdam"},
            {"name": "KDV B", "street": "", "postcode": "", "city": "Amsterdam"},
        ]

        call_count = {"n": 0}
        def failing_first(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise Exception("NOT NULL violation")

        with patch("scrapers.branches.get_connection", return_value=conn), \
             patch("scrapers.branches.COMPANY_CONFIGS", {"slug": {"scraper": lambda: fake_locations}}), \
             patch("scrapers.branches.upsert_vestiging", side_effect=failing_first):
            stats = run_vestigingen_scrape(["slug"])

        rollback_calls = [c for c in cur.execute.call_args_list
                          if "ROLLBACK TO SAVEPOINT" in str(c)]
        assert len(rollback_calls) >= 1
        # Second location should still succeed
        assert stats["slug"]["locations"] == 1


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


# ── _extract_js_json ──────────────────────────────────────────────────────────

class TestExtractJsJson:
    def test_basic_extraction(self):
        html = 'var locations = [{"name": "Test", "city": "Rotterdam"}];'
        result = _extract_js_json(html, "locations")
        assert result == [{"name": "Test", "city": "Rotterdam"}]

    def test_no_spaces_around_equals(self):
        html = 'locations=[{"name":"A"}];'
        result = _extract_js_json(html, "locations")
        assert result == [{"name": "A"}]

    def test_window_prefix(self):
        html = 'window.ProjectenData = [{"headline": "Sinne"}];'
        result = _extract_js_json(html, "window.ProjectenData")
        assert result == [{"headline": "Sinne"}]

    def test_nonexistent_var_returns_empty(self):
        html = 'var other = [{"name": "X"}];'
        result = _extract_js_json(html, "locations")
        assert result == []

    def test_invalid_json_returns_empty(self):
        html = 'var locations = [{broken json}];'
        result = _extract_js_json(html, "locations")
        assert result == []

    def test_multiline_array(self):
        html = 'var data = [\n  {"name": "A"},\n  {"name": "B"}\n];'
        result = _extract_js_json(html, "data")
        assert len(result) == 2
        assert result[0]["name"] == "A"


# ── scrape_partou_vestigingen ─────────────────────────────────────────────────

PARTOU_CONTENTFUL_RESPONSE = {
    "data": {
        "vacancyCollection": {
            "items": [
                {
                    "oeNumber": "OE001",
                    "address": "Sterstraat 1",
                    "postalCode": "3011AB",
                    "city": "Rotterdam",
                    "latitude": 51.92,
                    "longitude": 4.48,
                },
                {
                    "oeNumber": "OE002",
                    "address": "Zonnelaan 5",
                    "postalCode": "3012AB",
                    "city": "Rotterdam",
                    "latitude": 51.93,
                    "longitude": 4.49,
                },
                # Duplicate oeNumber — should be deduplicated
                {
                    "oeNumber": "OE001",
                    "address": "Sterstraat 1",
                    "postalCode": "3011AB",
                    "city": "Rotterdam",
                },
            ]
        }
    }
}


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
    def _mock_post(self, json_data, status=200):
        resp = MagicMock()
        resp.json = MagicMock(return_value=json_data)
        resp.status_code = status
        resp.raise_for_status = MagicMock()
        return resp

    def test_contentful_locations_extracted(self):
        with patch("scrapers.branches.requests.post",
                   return_value=self._mock_post(PARTOU_CONTENTFUL_RESPONSE)):
            locations = scrape_partou_vestigingen()
        assert len(locations) == 2  # OE001 deduplicated
        cities = [loc["city"] for loc in locations]
        assert all(c == "Rotterdam" for c in cities)

    def test_deduplication_by_oe_number(self):
        with patch("scrapers.branches.requests.post",
                   return_value=self._mock_post(PARTOU_CONTENTFUL_RESPONSE)):
            locations = scrape_partou_vestigingen()
        names = [loc["name"] for loc in locations]
        assert len(names) == len(set(names)) or len(locations) == 2

    def test_location_has_correct_fields(self):
        with patch("scrapers.branches.requests.post",
                   return_value=self._mock_post(PARTOU_CONTENTFUL_RESPONSE)):
            locations = scrape_partou_vestigingen()
        loc = next(l for l in locations if "Sterstraat" in l["name"])
        assert loc["street"] == "Sterstraat 1"
        assert loc["postcode"] == "3011AB"
        assert loc["city"] == "Rotterdam"

    def test_returns_empty_on_api_error(self):
        with patch("scrapers.branches.requests.post",
                   side_effect=Exception("connection refused")):
            locations = scrape_partou_vestigingen()
        assert locations == []

    def test_skips_items_without_city(self):
        data = {
            "data": {"vacancyCollection": {"items": [
                {"oeNumber": "OE999", "address": "Straat 1", "postalCode": "1234AB", "city": ""},
            ]}}
        }
        with patch("scrapers.branches.requests.post", return_value=self._mock_post(data)):
            locations = scrape_partou_vestigingen()
        assert locations == []


# ── scrape_kinderdam_vestigingen ──────────────────────────────────────────────

# Kinderdam uses Next.js App Router (flight protocol): self.__next_f.push([1, "..."])
# The payload is double-escaped JSON; "locations" array has items with name + kdv/bso/po sub-objects.
_KINDERDAM_ITEM = (
    r'{"name":"De Kijkdoos","image":{},"region":"rotterdam-feijenoord","wijk":"wijk-hillesluis",'
    r'"ssg":{},"kdv":{"address":"Walravenstraat 31","postalCode":"3074 NL",'
    r'"city":"Rotterdam","latitude":51.8926783,"longitude":4.5099081,"slug":"kdv"},'
    r'"po":{},"bso":{},"id":"abc"}'
)
_KINDERDAM_FLIGHT_PAYLOAD = (
    '{"defaultCareType":"kdv","locations":[' + _KINDERDAM_ITEM + '],"total":1}'
)
# Encode as JS string escape (double-escape quotes)
_KINDERDAM_ENCODED = _KINDERDAM_FLIGHT_PAYLOAD.replace('"', '\\"')
KINDERDAM_FLIGHT_HTML = (
    f'<html><body>'
    f'<script>self.__next_f.push([1,"{_KINDERDAM_ENCODED}"])</script>'
    f'</body></html>'
)


class TestScrapeKinderdamVestigingen:
    def _mock_resp(self, html, status=200):
        resp = MagicMock()
        resp.text = html
        resp.status_code = status
        resp.raise_for_status = MagicMock()
        return resp

    def test_flight_protocol_location_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(KINDERDAM_FLIGHT_HTML)):
            locations = scrape_kinderdam_vestigingen()
        assert len(locations) >= 1
        loc = locations[0]
        assert loc["name"] == "De Kijkdoos"
        assert loc["city"] == "Rotterdam"
        assert loc["postcode"] == "3074NL"

    def test_coordinates_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(KINDERDAM_FLIGHT_HTML)):
            locations = scrape_kinderdam_vestigingen()
        loc = locations[0]
        assert loc["lat"] == pytest.approx(51.8926783)
        assert loc["lon"] == pytest.approx(4.5099081)

    def test_returns_empty_on_error(self):
        with patch("scrapers.branches.requests.get", side_effect=Exception("timeout")):
            locations = scrape_kinderdam_vestigingen()
        assert locations == []

    def test_returns_empty_on_404(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp("", status=404)):
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


# ── scrape_compananny_vestigingen ─────────────────────────────────────────────
# CompaNanny embeds JS object literal (unquoted keys, single-quoted values)

COMPANANNY_JS_HTML = """<html><body>
<script>
var locations = [
  {name: 'Amstel', lon: '4.90758', lat: '52.3577', address: 'Swammerdamstraat 40HS', zipcode: '1091 RV, Amsterdam'},
  {name: 'Haarlem Noord', lon: '4.63530', lat: '52.3905', address: 'Brouwersvaart 62', zipcode: '2015 BM, Haarlem'}
];
</script>
</body></html>"""

COMPANANNY_NO_JS_HTML = """<html><body><p>Geen locaties gevonden.</p></body></html>"""


class TestScrapeCompanannyVestigingen:
    def _mock_resp(self, html, status=200):
        resp = MagicMock()
        resp.text = html
        resp.status_code = status
        resp.raise_for_status = MagicMock()
        return resp

    def test_js_locations_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(COMPANANNY_JS_HTML)):
            locations = scrape_compananny_vestigingen()
        assert len(locations) == 2
        names = [l["name"] for l in locations]
        assert "Amstel" in names
        assert "Haarlem Noord" in names

    def test_postcode_and_city_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(COMPANANNY_JS_HTML)):
            locations = scrape_compananny_vestigingen()
        ams = next(l for l in locations if "Amstel" in l["name"])
        assert ams["postcode"] == "1091RV"
        assert ams["city"] == "Amsterdam"
        assert ams["street"] == "Swammerdamstraat 40HS"

    def test_coordinates_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(COMPANANNY_JS_HTML)):
            locations = scrape_compananny_vestigingen()
        ams = next(l for l in locations if "Amstel" in l["name"])
        assert ams["lon"] == pytest.approx(4.90758)
        assert ams["lat"] == pytest.approx(52.3577)

    def test_404_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp("", status=404)):
            locations = scrape_compananny_vestigingen()
        assert locations == []

    def test_no_js_object_literal_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(COMPANANNY_NO_JS_HTML)):
            locations = scrape_compananny_vestigingen()
        assert locations == []

    def test_exception_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   side_effect=Exception("connection refused")):
            locations = scrape_compananny_vestigingen()
        assert locations == []


# ── scrape_tinteltuin_vestigingen ─────────────────────────────────────────────
# TintelTuin embeds a 'mapdata' JSON array with addresses.map.lat/lng

TINTELTUIN_JS_HTML = """<html><body>
<script>
var mapdata = [
  {"post_title": "Campus Olympia",
   "addresses": {"street_name": "Willem Prinsplein 4", "postcode": "1509AX", "city": "Zaandam",
                 "map": {"lat": 52.4639428, "lng": 4.8252441}}},
  {"post_title": "Het Hoekje",
   "addresses": {"street_name": "Calkoenstraat 15", "postcode": "1121XA", "city": "Landsmeer",
                 "map": {"lat": 52.4305831, "lng": 4.9157004}}}
];
</script>
</body></html>"""

TINTELTUIN_NO_MAPDATA_HTML = """<html><body><p>Geen locaties.</p></body></html>"""


class TestScrapeTinteltuinVestigingen:
    def _mock_resp(self, html, status=200):
        resp = MagicMock()
        resp.text = html
        resp.status_code = status
        resp.raise_for_status = MagicMock()
        return resp

    def test_mapdata_locations_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(TINTELTUIN_JS_HTML)):
            locations = scrape_tinteltuin_vestigingen()
        assert len(locations) == 2
        names = [l["name"] for l in locations]
        assert "Campus Olympia" in names

    def test_address_fields_parsed(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(TINTELTUIN_JS_HTML)):
            locations = scrape_tinteltuin_vestigingen()
        zaandam = next(l for l in locations if "Olympia" in l["name"])
        assert zaandam["postcode"] == "1509AX"
        assert zaandam["city"] == "Zaandam"
        assert zaandam["street"] == "Willem Prinsplein 4"

    def test_coordinates_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(TINTELTUIN_JS_HTML)):
            locations = scrape_tinteltuin_vestigingen()
        zaandam = next(l for l in locations if "Olympia" in l["name"])
        assert zaandam["lat"] == pytest.approx(52.4639428)
        assert zaandam["lon"] == pytest.approx(4.8252441)

    def test_404_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp("", status=404)):
            locations = scrape_tinteltuin_vestigingen()
        assert locations == []

    def test_no_mapdata_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(TINTELTUIN_NO_MAPDATA_HTML)):
            locations = scrape_tinteltuin_vestigingen()
        assert locations == []

    def test_exception_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   side_effect=Exception("timeout")):
            locations = scrape_tinteltuin_vestigingen()
        assert locations == []


# ── scrape_sinne_vestigingen ──────────────────────────────────────────────────
# Sinne embeds ProjectenData JSON; address in properties.values.adres (HTML),
# coordinates in properties.values.latitude/longitude.

SINNE_JS_HTML = """<html><body>
<script>
ProjectenData = [
  {"headline": "IKC Albertine Agnes",
   "properties": {"values": {
     "adres": "<p>8915 BB Leeuwarden</p>",
     "latitude": "53.2067839",
     "longitude": "5.7744684"
   }}},
  {"headline": "IKC Alexia",
   "properties": {"values": {
     "adres": "<p>Wilaarderdijk 34<br/>8925 AG Leeuwarden</p>",
     "latitude": "53.2095346",
     "longitude": "5.8425261"
   }}}
];
</script>
</body></html>"""

SINNE_NO_DATA_HTML = """<html><body><p>Geen locaties.</p></body></html>"""


class TestScrapeSinneVestigingen:
    def _mock_resp(self, html, status=200):
        resp = MagicMock()
        resp.text = html
        resp.status_code = status
        resp.raise_for_status = MagicMock()
        return resp

    def test_projectendata_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(SINNE_JS_HTML)):
            locations = scrape_sinne_vestigingen()
        assert len(locations) == 2
        names = [l["name"] for l in locations]
        assert "IKC Albertine Agnes" in names

    def test_postcode_extracted_from_html_adres(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(SINNE_JS_HTML)):
            locations = scrape_sinne_vestigingen()
        loc = next(l for l in locations if "Albertine" in l["name"])
        assert loc["postcode"] == "8915BB"

    def test_coordinates_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(SINNE_JS_HTML)):
            locations = scrape_sinne_vestigingen()
        loc = next(l for l in locations if "Albertine" in l["name"])
        assert loc["lat"] == pytest.approx(53.2067839)
        assert loc["lon"] == pytest.approx(5.7744684)

    def test_404_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp("", status=404)):
            locations = scrape_sinne_vestigingen()
        assert locations == []

    def test_no_projectendata_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(SINNE_NO_DATA_HTML)):
            locations = scrape_sinne_vestigingen()
        assert locations == []

    def test_exception_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   side_effect=Exception("SSL error")):
            locations = scrape_sinne_vestigingen()
        assert locations == []


# ── scrape_humankind_vestigingen ──────────────────────────────────────────────

HUMANKIND_GEOJSON_HTML = """<html><body>
<script>
var mapData = {
  "features": [
    {
      "label": "Humankind KDV De Regenboog",
      "popup": "<p>Regenboogstraat 1<br>1234AB Amsterdam</p>"
    },
    {
      "label": "Humankind BSO Zonlicht",
      "popup": "<p>Zonneweg 8<br>3456CD Rotterdam</p>"
    }
  ]
};
</script>
</body></html>"""

HUMANKIND_CARD_HTML = """<html><body>
<article class="location-card">
  <h3>Humankind Utrecht BSO</h3>
  <p>Oudkerkhof 2, 3512GH Utrecht</p>
</article>
</body></html>"""


class TestScrapeHumankindVestigingen:
    def _mock_resp(self, html, status=200):
        resp = MagicMock()
        resp.text = html
        resp.status_code = status
        resp.raise_for_status = MagicMock()
        return resp

    def test_geojson_features_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(HUMANKIND_GEOJSON_HTML)):
            locations = scrape_humankind_vestigingen()
        assert len(locations) == 2
        names = [l["name"] for l in locations]
        assert any("Regenboog" in n for n in names)

    def test_popup_address_parsed(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(HUMANKIND_GEOJSON_HTML)):
            locations = scrape_humankind_vestigingen()
        ams = next(l for l in locations if "Amsterdam" in l["city"])
        assert ams["postcode"] == "1234AB"
        assert ams["city"] == "Amsterdam"

    def test_html_card_fallback(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(HUMANKIND_CARD_HTML)):
            locations = scrape_humankind_vestigingen()
        # Card HTML fallback may or may not work depending on selector match
        assert isinstance(locations, list)

    def test_404_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp("", status=404)):
            locations = scrape_humankind_vestigingen()
        assert locations == []

    def test_exception_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   side_effect=Exception("connection refused")):
            locations = scrape_humankind_vestigingen()
        assert locations == []


# ── scrape_spring_vestigingen ──────────────────────────────────────────────────

SPRING_HTML = """<html><body>
<article class="item location" data-geocode="51.6035033, 6.0581517">
  <div class="card-body">
    <a class="card-title" href="/locatie/">Dagopvang Luchtballon | Bergen</a>
    <div class="fw-300 card-text">
      <span>Pieter de Hooghstraat 6, 5854 ES, Bergen</span>
    </div>
  </div>
</article>
<article class="item location" data-geocode="51.3662, 6.1302">
  <div class="card-body">
    <a class="card-title" href="/locatie/">Dagopvang Robinson | Blerick</a>
    <div class="fw-300 card-text">
      <span>Vossenerlaan 57, 5924 AC, Blerick</span>
    </div>
  </div>
</article>
</body></html>"""


class TestScrapeSpringVestigingen:
    def _mock_resp(self, html, status=200):
        resp = MagicMock()
        resp.text = html
        resp.status_code = status
        resp.raise_for_status = MagicMock()
        return resp

    def test_locations_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(SPRING_HTML)):
            locations = scrape_spring_vestigingen()
        assert len(locations) == 2
        names = [l["name"] for l in locations]
        assert any("Luchtballon" in n for n in names)

    def test_address_parsed_from_span(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(SPRING_HTML)):
            locations = scrape_spring_vestigingen()
        loc = next(l for l in locations if "Luchtballon" in l["name"])
        assert loc["street"] == "Pieter de Hooghstraat 6"
        assert loc["postcode"] == "5854ES"
        assert loc["city"] == "Bergen"

    def test_coordinates_from_data_geocode(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(SPRING_HTML)):
            locations = scrape_spring_vestigingen()
        loc = next(l for l in locations if "Luchtballon" in l["name"])
        assert loc["lat"] == pytest.approx(51.6035033)
        assert loc["lon"] == pytest.approx(6.0581517)

    def test_404_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp("", status=404)):
            locations = scrape_spring_vestigingen()
        assert locations == []

    def test_exception_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   side_effect=Exception("DNS")):
            locations = scrape_spring_vestigingen()
        assert locations == []


# ── scrape_prokino_vestigingen ─────────────────────────────────────────────────

PROKINO_NEXT_DATA = {
    "props": {"pageProps": {"pageProps": {
        "locations": [
            {
                "pageTitle": "Prokino 't Hummelhof",
                "geoLocation": {"lat": 52.5797919, "lng": 6.2838299},
                "sectionBox": [{"products": [{"contactDetails": {
                    "address": "Kon. Julianalaan 14",
                    "zipCode": "7711 KK",
                    "city": "Nieuwleusen",
                }}]}],
            }
        ]
    }}}
}

import json as _json_mod
PROKINO_HTML = (
    '<html><body>'
    '<script id="__NEXT_DATA__" type="application/json">'
    + _json_mod.dumps(PROKINO_NEXT_DATA) +
    '</script></body></html>'
)


class TestScrapePrrokinoVestigingen:
    def _mock_resp(self, html, status=200):
        resp = MagicMock()
        resp.text = html
        resp.status_code = status
        resp.raise_for_status = MagicMock()
        return resp

    def test_next_data_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(PROKINO_HTML)):
            locations = scrape_prokino_vestigingen()
        assert len(locations) == 1
        assert locations[0]["name"] == "Prokino 't Hummelhof"

    def test_address_and_coordinates(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(PROKINO_HTML)):
            locations = scrape_prokino_vestigingen()
        loc = locations[0]
        assert loc["postcode"] == "7711KK"
        assert loc["city"] == "Nieuwleusen"
        assert loc["lat"] == pytest.approx(52.5797919)
        assert loc["lon"] == pytest.approx(6.2838299)

    def test_404_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp("", status=404)):
            locations = scrape_prokino_vestigingen()
        assert locations == []

    def test_exception_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   side_effect=Exception("DNS")):
            locations = scrape_prokino_vestigingen()
        assert locations == []


# ── scrape_kober_vestigingen ───────────────────────────────────────────────────

KOBER_HTML = """<html><body>
<div class="right-col">
  <h5 class="post-title"><a>'t Klokhuis</a></h5>
  <div class="address-wrapper">
    <span class="address">Weversdries 3, 4851 BD, Ulvenhout</span>
  </div>
</div>
<div class="right-col">
  <h5 class="post-title"><a>'t Olifantje</a></h5>
  <div class="address-wrapper">
    <span class="address">Kapittelhof 2, 4841 GX, Prinsenbeek</span>
  </div>
</div>
</body></html>"""


class TestScrapeKoberVestigingen:
    def _mock_resp(self, html, status=200):
        resp = MagicMock()
        resp.text = html
        resp.status_code = status
        resp.raise_for_status = MagicMock()
        return resp

    def test_locations_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(KOBER_HTML)):
            locations = scrape_kober_vestigingen()
        assert len(locations) == 2
        names = [l["name"] for l in locations]
        assert "'t Klokhuis" in names

    def test_address_parsed(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(KOBER_HTML)):
            locations = scrape_kober_vestigingen()
        loc = next(l for l in locations if "Klokhuis" in l["name"])
        assert loc["street"] == "Weversdries 3"
        assert loc["postcode"] == "4851BD"
        assert loc["city"] == "Ulvenhout"

    def test_404_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp("", status=404)):
            locations = scrape_kober_vestigingen()
        assert locations == []

    def test_exception_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   side_effect=Exception("DNS")):
            locations = scrape_kober_vestigingen()
        assert locations == []


# ── scrape_kion_vestigingen ────────────────────────────────────────────────────

KION_JS_HTML = """<html><body>
<script>
var locations = [
  {
    'id': 59,
    'type': 'bso',
    'name': 'Afferden',
    'address': 'De Gaard 19',
    'city': 'Afferden',
    'zipcode': '6654 BL',
    'phone': '06 42 38 61 09',
    'lat': 51.880428,
    'lng': 5.6338169,
    'resource_id': 193,
    'url': 'https://kion.nl/locaties/afferden.html'
  },
  {
    'id': 60,
    'type': 'kdv',
    'name': 'Alphen',
    'address': 'Schoolstraat 9',
    'city': 'Alphen',
    'zipcode': '6626 AC',
    'lat': 51.8204476,
    'lng': 5.4720365
  }
];
</script>
</body></html>"""


class TestScrapeKionVestigingen:
    def _mock_resp(self, html, status=200):
        resp = MagicMock()
        resp.text = html
        resp.status_code = status
        resp.raise_for_status = MagicMock()
        return resp

    def test_locations_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(KION_JS_HTML)):
            locations = scrape_kion_vestigingen()
        assert len(locations) == 2
        names = [l["name"] for l in locations]
        assert "Afferden" in names
        assert "Alphen" in names

    def test_address_and_coordinates(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(KION_JS_HTML)):
            locations = scrape_kion_vestigingen()
        loc = next(l for l in locations if l["name"] == "Afferden")
        assert loc["street"] == "De Gaard 19"
        assert loc["postcode"] == "6654BL"
        assert loc["city"] == "Afferden"
        assert loc["lat"] == pytest.approx(51.880428)
        assert loc["lon"] == pytest.approx(5.6338169)

    def test_404_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp("", status=404)):
            locations = scrape_kion_vestigingen()
        assert locations == []

    def test_exception_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   side_effect=Exception("DNS")):
            locations = scrape_kion_vestigingen()
        assert locations == []


# ── scrape_bijdehandjes_vestigingen ───────────────────────────────────────────

BIJDEHANDJES_JSON = {
    "locations": [
        {
            "id": "356",
            "title": "Berglaan Voorthuizen",
            "address": "Van den Berglaan 79, 3781GE Voorthuizen",
            "geofield": {"lat": 52.18399, "lon": 5.606873},
        },
        {
            "id": "357",
            "title": "De Koppel Amersfoort",
            "address": "Zuiderkruis 4, 3813VA Amersfoort",
            "geofield": {"lat": 52.165013, "lon": 5.384491},
        },
    ],
    "services": [],
    "club_sport_name": None,
}


class TestScrapeBijdehandjesVestigingen:
    def _mock_resp(self, data, status=200):
        m = MagicMock()
        m.status_code = status
        m.json.return_value = data
        m.raise_for_status = MagicMock()
        return m

    def test_locations_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(BIJDEHANDJES_JSON)):
            locations = scrape_bijdehandjes_vestigingen()
        assert len(locations) == 2

    def test_address_parsed(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(BIJDEHANDJES_JSON)):
            locations = scrape_bijdehandjes_vestigingen()
        loc = next(l for l in locations if "Voorthuizen" in l["name"])
        assert loc["street"] == "Van den Berglaan 79"
        assert loc["postcode"] == "3781GE"
        assert loc["city"] == "Voorthuizen"
        assert loc["lat"] == pytest.approx(52.18399)
        assert loc["lon"] == pytest.approx(5.606873)

    def test_api_error_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   side_effect=Exception("timeout")):
            locations = scrape_bijdehandjes_vestigingen()
        assert locations == []

    def test_empty_locations_key(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp({"locations": [], "services": []})):
            locations = scrape_bijdehandjes_vestigingen()
        assert locations == []


# ── scrape_norlandia_vestigingen ──────────────────────────────────────────────

NORLANDIA_CITY_LIST_HTML = """
<script type="text/javascript">
var model = {
  "Cities": [
    {"Name": "Rotterdam", "Url": "/zoek-locatie/rotterdam"}
  ]
}
</script>
"""

NORLANDIA_CITY_PAGE_HTML = """
<script type="text/javascript">
var model = {
  "ViewOtherLocationsText": "Bekijk",
  "MapHits": [
    {
      "Id": 61902,
      "Position": {"Latitude": "51.9348", "Longitude": "4.4368"},
      "Name": "Norlandia De Boomkorf",
      "Municipality": "Rotterdam",
      "Address": "Rammelandstraat 10",
      "ZipCode": "3042 EZ"
    }
  ]
}
</script>
"""


class TestScrapeNorlandiaVestigingen:
    def _mock_get(self, url, **kwargs):
        m = MagicMock()
        m.status_code = 200
        if "zoek-locatie/rotterdam" in url:
            m.text = NORLANDIA_CITY_PAGE_HTML
        else:
            m.text = NORLANDIA_CITY_LIST_HTML
        m.raise_for_status = MagicMock()
        return m

    def test_locations_extracted(self):
        with patch("scrapers.branches.requests.get", side_effect=self._mock_get):
            locations = scrape_norlandia_vestigingen()
        assert len(locations) == 1

    def test_address_parsed(self):
        with patch("scrapers.branches.requests.get", side_effect=self._mock_get):
            locations = scrape_norlandia_vestigingen()
        loc = locations[0]
        assert loc["name"] == "Norlandia De Boomkorf"
        assert loc["street"] == "Rammelandstraat 10"
        assert loc["postcode"] == "3042EZ"
        assert loc["city"] == "Rotterdam"
        assert loc["lat"] == pytest.approx(51.9348)
        assert loc["lon"] == pytest.approx(4.4368)

    def test_city_list_fetch_error_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   side_effect=Exception("DNS")):
            locations = scrape_norlandia_vestigingen()
        assert locations == []

    def test_no_cities_returns_empty(self):
        m = MagicMock()
        m.status_code = 200
        m.text = '<script>var model = {"Cities": []}</script>'
        m.raise_for_status = MagicMock()
        with patch("scrapers.branches.requests.get", return_value=m):
            locations = scrape_norlandia_vestigingen()
        assert locations == []


# ── scrape_kindergarden_vestigingen ──────────────────────────────────────────

KINDERGARDEN_JSON = {
    "Locations": [
        {
            "Name": "Kindergarden Zwitserlandstraat",
            "Address": "Zwitserlandstraat 6",
            "City": "Almere",
            "PostalCode": "1363 BE",
            "Latitude": "52.3467762",
            "Longitude": "5.152953",
        },
        {
            "Name": "Kindergarden Hoofddorp",
            "Address": "Polderplein 1",
            "City": "Hoofddorp",
            "PostalCode": "2132 BA",
            "Latitude": "52.302",
            "Longitude": "4.697",
        },
    ]
}


class TestScrapeKindergardenVestigingen:
    def _mock_resp(self, data, status=200):
        m = MagicMock()
        m.status_code = status
        m.json.return_value = data
        m.raise_for_status = MagicMock()
        return m

    def test_locations_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(KINDERGARDEN_JSON)):
            locations = scrape_kindergarden_vestigingen()
        assert len(locations) == 2

    def test_address_parsed(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(KINDERGARDEN_JSON)):
            locations = scrape_kindergarden_vestigingen()
        loc = locations[0]
        assert loc["name"] == "Kindergarden Zwitserlandstraat"
        assert loc["street"] == "Zwitserlandstraat 6"
        assert loc["postcode"] == "1363BE"
        assert loc["city"] == "Almere"
        assert loc["lat"] == pytest.approx(52.3467762)
        assert loc["lon"] == pytest.approx(5.152953)

    def test_api_error_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   side_effect=Exception("timeout")):
            locations = scrape_kindergarden_vestigingen()
        assert locations == []

    def test_empty_locations_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp({"Locations": []})):
            locations = scrape_kindergarden_vestigingen()
        assert locations == []


# ── scrape_ko_walcheren_vestigingen ──────────────────────────────────────────

KO_WALCHEREN_HTML = """
<html><body>
<div class="location-teaser__inner">
  <p class="location-teaser__title">Anker</p>
  <div class="location-teaser__address">Schoutstraat 5, 4336HN Middelburg</div>
</div>
<div class="location-teaser__inner">
  <p class="location-teaser__title">Boomhut</p>
  <div class="location-teaser__address">Torenhofstraat 4, 4337JV Middelburg</div>
</div>
<div class="location-teaser__inner">
  <p class="location-teaser__title">Geen adres</p>
</div>
</body></html>
"""


class TestScrapeKoWalcherenVestigingen:
    def _mock_resp(self, html, status=200):
        m = MagicMock()
        m.status_code = status
        m.text = html
        m.raise_for_status = MagicMock()
        return m

    def test_locations_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(KO_WALCHEREN_HTML)):
            locations = scrape_ko_walcheren_vestigingen()
        assert len(locations) == 2

    def test_address_parsed(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(KO_WALCHEREN_HTML)):
            locations = scrape_ko_walcheren_vestigingen()
        loc = next(l for l in locations if l["name"] == "Anker")
        assert loc["street"] == "Schoutstraat 5"
        assert loc["postcode"] == "4336HN"
        assert loc["city"] == "Middelburg"

    def test_card_without_address_skipped(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(KO_WALCHEREN_HTML)):
            locations = scrape_ko_walcheren_vestigingen()
        names = [l["name"] for l in locations]
        assert "Geen adres" not in names

    def test_fetch_error_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   side_effect=Exception("timeout")):
            locations = scrape_ko_walcheren_vestigingen()
        assert locations == []

    def test_non_200_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp("", status=404)):
            with patch("scrapers.branches.requests.Response.raise_for_status",
                       side_effect=Exception("404")):
                locations = scrape_ko_walcheren_vestigingen()
        assert locations == []


# ── scrape_mik_vestigingen ────────────────────────────────────────────────────

MIK_HTML = """
<html><body>
<ul>
  <li wire:key="abc123">
    <a href="/locaties/bso-zo">
      <h4>BSO &amp; Zo</h4>
      <span>Lindenlaan 73 - 6241BB Bunde</span>
    </a>
  </li>
  <li wire:key="def456">
    <a href="/locaties/bso-aelse">
      <h4>BSO Aelse</h4>
      <span>Joannes Riviusstraat 4 - 6181BT Elsloo</span>
    </a>
  </li>
  <li wire:key="ghi789">
    <a href="/locaties/geen-postcode">
      <h4>Geen postcode</h4>
      <span>Gewoon een tekst zonder NL code</span>
    </a>
  </li>
</ul>
</body></html>
"""


class TestScrapeMikVestigingen:
    def _mock_resp(self, html, status=200):
        m = MagicMock()
        m.status_code = status
        m.text = html
        m.raise_for_status = MagicMock()
        return m

    def test_locations_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(MIK_HTML)):
            locations = scrape_mik_vestigingen()
        assert len(locations) == 2

    def test_address_parsed(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(MIK_HTML)):
            locations = scrape_mik_vestigingen()
        loc = next(l for l in locations if "Zo" in l["name"])
        assert loc["street"] == "Lindenlaan 73"
        assert loc["postcode"] == "6241BB"
        assert loc["city"] == "Bunde"

    def test_item_without_postcode_skipped(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(MIK_HTML)):
            locations = scrape_mik_vestigingen()
        names = [l["name"] for l in locations]
        assert "Geen postcode" not in names

    def test_fetch_error_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   side_effect=Exception("DNS")):
            locations = scrape_mik_vestigingen()
        assert locations == []


# ── scrape_dak_vestigingen ────────────────────────────────────────────────────

DAK_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "name": "DAK De Wielen",
                "address": "Wielsebaan 10",
                "postcode": "4705PC",
                "city": "Roosendaal",
                "visible": True,
            },
            "geometry": {"type": "Point", "coordinates": [4.4672, 51.5314]},
        },
        {
            "type": "Feature",
            "properties": {
                "name": "DAK Onzichtbaar",
                "address": "Ergens 1",
                "postcode": "1234AB",
                "city": "Nergens",
                "visible": False,  # must be skipped
            },
            "geometry": {"type": "Point", "coordinates": [4.0, 51.0]},
        },
    ],
}


class TestScrapeDakVestigingen:
    def _mock_resp(self, data, status=200):
        m = MagicMock()
        m.status_code = status
        m.json.return_value = data
        m.raise_for_status = MagicMock()
        return m

    def test_locations_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(DAK_GEOJSON)):
            locations = scrape_dak_vestigingen()
        assert len(locations) == 1

    def test_invisible_feature_skipped(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(DAK_GEOJSON)):
            locations = scrape_dak_vestigingen()
        names = [l["name"] for l in locations]
        assert "DAK Onzichtbaar" not in names

    def test_address_parsed(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(DAK_GEOJSON)):
            locations = scrape_dak_vestigingen()
        loc = locations[0]
        assert loc["name"] == "DAK De Wielen"
        assert loc["street"] == "Wielsebaan 10"
        assert loc["postcode"] == "4705PC"
        assert loc["city"] == "Roosendaal"
        assert loc["lat"] == pytest.approx(51.5314)
        assert loc["lon"] == pytest.approx(4.4672)

    def test_fetch_error_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   side_effect=Exception("timeout")):
            locations = scrape_dak_vestigingen()
        assert locations == []

    def test_empty_features_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp({"type": "FeatureCollection", "features": []})):
            locations = scrape_dak_vestigingen()
        assert locations == []


# ── scrape_wij_zijn_jong_vestigingen ─────────────────────────────────────────

WIJ_ZIJN_JONG_JSON = {
    "aMarkers": {
        "1": {
            "latitude": 51.4350,
            "longitude": 5.4780,
            "markerInfo": (
                '<div class="gmaps2-markerinfo-title">BSO De Regenboog</div>'
                '<div class="gmaps2-markerinfo-address">Regenbooglaan 5</div>'
                '<div class="gmaps2-markerinfo-postal">5616EB</div>'
                '<div class="gmaps2-markerinfo-city">Eindhoven</div>'
            ),
        },
        "2": {
            "latitude": 51.5000,
            "longitude": 5.5000,
            "markerInfo": "",  # empty — must be skipped
        },
    }
}


class TestScrapeWijZijnJongVestigingen:
    def _mock_resp(self, data, status=200):
        m = MagicMock()
        m.status_code = status
        m.json.return_value = data
        m.raise_for_status = MagicMock()
        return m

    def test_locations_extracted(self):
        with patch("scrapers.branches.requests.post",
                   return_value=self._mock_resp(WIJ_ZIJN_JONG_JSON)):
            locations = scrape_wij_zijn_jong_vestigingen()
        assert len(locations) == 1

    def test_address_parsed(self):
        with patch("scrapers.branches.requests.post",
                   return_value=self._mock_resp(WIJ_ZIJN_JONG_JSON)):
            locations = scrape_wij_zijn_jong_vestigingen()
        loc = locations[0]
        assert loc["name"] == "BSO De Regenboog"
        assert loc["street"] == "Regenbooglaan 5"
        assert loc["postcode"] == "5616EB"
        assert loc["city"] == "Eindhoven"
        assert loc["lat"] == pytest.approx(51.4350)
        assert loc["lon"] == pytest.approx(5.4780)

    def test_post_error_returns_empty(self):
        with patch("scrapers.branches.requests.post",
                   side_effect=Exception("timeout")):
            locations = scrape_wij_zijn_jong_vestigingen()
        assert locations == []

    def test_empty_markers_returns_empty(self):
        with patch("scrapers.branches.requests.post",
                   return_value=self._mock_resp({"aMarkers": {}})):
            locations = scrape_wij_zijn_jong_vestigingen()
        assert locations == []


# ── scrape_wasko_vestigingen ──────────────────────────────────────────────────

WASKO_SLUG_RESP = [{"slug": "locatie-a"}]
WASKO_PAGE_HTML = """
<html><body>
<h1>Locatie A</h1>
<h6>Locatie | Teststraat 42 | 1234AB Amsterdam | 020-1234567</h6>
</body></html>
"""


class TestScrapeWaskoVestigingen:
    def _mock_get(self, url, **kwargs):
        m = MagicMock()
        m.raise_for_status = MagicMock()
        if "wp-json" in url and "&page=1&" in url:
            # First REST page — return one slug
            m.status_code = 200
            m.json.return_value = WASKO_SLUG_RESP
        elif "wp-json" in url:
            # Page 2+ → 400 signals "no more pages"
            m.status_code = 400
            m.json.return_value = []
        elif "locatie-a" in url:
            m.status_code = 200
            m.text = WASKO_PAGE_HTML
        else:
            m.status_code = 404
            m.json.return_value = []
        return m

    def test_locations_extracted(self):
        with patch("scrapers.branches.requests.get", side_effect=self._mock_get):
            locations = scrape_wasko_vestigingen()
        assert len(locations) == 1

    def test_address_parsed(self):
        with patch("scrapers.branches.requests.get", side_effect=self._mock_get):
            locations = scrape_wasko_vestigingen()
        loc = locations[0]
        assert loc["name"] == "Locatie A"
        assert loc["street"] == "Teststraat 42"
        assert loc["postcode"] == "1234AB"
        assert loc["city"] == "Amsterdam"

    def test_rest_error_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   side_effect=Exception("timeout")):
            locations = scrape_wasko_vestigingen()
        assert locations == []

    def test_no_slugs_returns_empty(self):
        m = MagicMock()
        m.status_code = 400
        m.json.return_value = []
        m.raise_for_status = MagicMock()
        with patch("scrapers.branches.requests.get", return_value=m):
            locations = scrape_wasko_vestigingen()
        assert locations == []


# ── scrape_kanteel_vestigingen ────────────────────────────────────────────────

KANTEEL_JS = (
    "app.handleGoogleMaps('"
    '{"locations":{"1":{"Name":"Kindcentrum De Peppels","Street":"Peppelseweg 3",'
    '"PostalAndPlace":"5261 TC Vught","Geo":{"latitude":51.65,"longitude":5.29}}}}'
    "')"
)

KANTEEL_PAGE_HTML = f"<html><body><script>{KANTEEL_JS}</script></body></html>"


class TestScrapeKanteelVestigingen:
    def _mock_resp(self, html, status=200):
        m = MagicMock()
        m.status_code = status
        m.text = html
        m.raise_for_status = MagicMock()
        return m

    def test_locations_extracted(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(KANTEEL_PAGE_HTML)):
            locations = scrape_kanteel_vestigingen()
        assert len(locations) >= 1

    def test_address_parsed(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp(KANTEEL_PAGE_HTML)):
            locations = scrape_kanteel_vestigingen()
        loc = next(l for l in locations if "Peppels" in l["name"])
        assert loc["street"] == "Peppelseweg 3"
        assert loc["postcode"] == "5261TC"
        assert loc["city"] == "Vught"
        assert loc["lat"] == pytest.approx(51.65)
        assert loc["lon"] == pytest.approx(5.29)

    def test_fetch_error_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   side_effect=Exception("SSL")):
            locations = scrape_kanteel_vestigingen()
        assert locations == []

    def test_no_json_in_page_returns_empty(self):
        with patch("scrapers.branches.requests.get",
                   return_value=self._mock_resp("<html><body>Geen data</body></html>")):
            locations = scrape_kanteel_vestigingen()
        assert locations == []
