"""
Unit tests for BaseScraper and base module helpers.
Uses mocked DB connections and PDOK API.
"""
import sys, os, pytest
from unittest.mock import patch, MagicMock, call
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrapers.base import (
    _geocode_via_pdok,
    geocode_locations,
    BaseScraper,
    PDOK_URL,
)


# ── _geocode_via_pdok ─────────────────────────────────────────────────────────

class TestGeocodeViaPdok:
    PDOK_RESPONSE = {
        "response": {
            "docs": [{
                "centroide_ll": "POINT(4.895168 52.370216)",
                "woonplaatsnaam": "Amsterdam",
                "postcode": "1012AB",
                "gemeentenaam": "Amsterdam",
            }]
        }
    }

    def test_returns_geo_dict(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = self.PDOK_RESPONSE
        with patch("scrapers.base.requests.get", return_value=mock_resp) as mock_get:
            result = _geocode_via_pdok("Amsterdam")
        assert result["city"] == "Amsterdam"
        assert result["lon"] == pytest.approx(4.895168)
        assert result["lat"] == pytest.approx(52.370216)
        assert result["postcode"] == "1012AB"
        assert result["municipality"] == "Amsterdam"
        mock_get.assert_called_once_with(
            PDOK_URL,
            params=pytest.approx({
                "q": "Amsterdam",
                "fq": "bron:BAG",
                "rows": 1,
                "fl": "centroide_ll,woonplaatsnaam,postcode,gemeentenaam",
            }),
            timeout=10,
        )

    def test_returns_none_when_no_docs(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"response": {"docs": []}}
        with patch("scrapers.base.requests.get", return_value=mock_resp):
            result = _geocode_via_pdok("UnknownCity")
        assert result is None

    def test_returns_none_on_missing_centroide(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "response": {"docs": [{"woonplaatsnaam": "Amsterdam"}]}
        }
        with patch("scrapers.base.requests.get", return_value=mock_resp):
            result = _geocode_via_pdok("Amsterdam")
        assert result is None

    def test_returns_none_on_request_error(self):
        with patch("scrapers.base.requests.get", side_effect=Exception("timeout")):
            result = _geocode_via_pdok("Amsterdam")
        assert result is None


# ── geocode_locations ─────────────────────────────────────────────────────────

class TestGeocodeLocations:
    def test_returns_empty_for_empty_set(self):
        cur = MagicMock()
        result = geocode_locations(cur, set())
        assert result == {}
        cur.execute.assert_not_called()

    def test_uses_cache_from_db(self):
        cur = MagicMock()
        cur.fetchall.return_value = [
            ("Amsterdam", "Amsterdam", "1012AB", "Amsterdam", 4.895, 52.370)
        ]
        result = geocode_locations(cur, {"Amsterdam"})
        assert "Amsterdam" in result
        assert result["Amsterdam"]["city"] == "Amsterdam"
        assert result["Amsterdam"]["lon"] == 4.895

    def test_calls_pdok_for_uncached_location(self):
        cur = MagicMock()
        cur.fetchall.return_value = []  # Nothing in cache
        geo = {"city": "Utrecht", "postcode": "3511AB", "municipality": "Utrecht",
               "lon": 5.12, "lat": 52.09}
        with patch("scrapers.base._geocode_via_pdok", return_value=geo):
            result = geocode_locations(cur, {"Utrecht"})
        assert "Utrecht" in result
        assert result["Utrecht"]["city"] == "Utrecht"
        # Should insert into cache
        assert cur.execute.call_count == 2  # SELECT + INSERT

    def test_skips_insert_when_pdok_returns_none(self):
        cur = MagicMock()
        cur.fetchall.return_value = []
        with patch("scrapers.base._geocode_via_pdok", return_value=None):
            result = geocode_locations(cur, {"Unknown"})
        assert result == {}
        assert cur.execute.call_count == 1  # Only SELECT, no INSERT

    def test_combines_cache_and_pdok(self):
        cur = MagicMock()
        cur.fetchall.return_value = [
            ("Amsterdam", "Amsterdam", "1012AB", "Amsterdam", 4.895, 52.370)
        ]
        geo_utrecht = {"city": "Utrecht", "postcode": "3511AB", "municipality": "Utrecht",
                       "lon": 5.12, "lat": 52.09}
        with patch("scrapers.base._geocode_via_pdok", return_value=geo_utrecht):
            result = geocode_locations(cur, {"Amsterdam", "Utrecht"})
        assert "Amsterdam" in result
        assert "Utrecht" in result


# ── BaseScraper._upsert_company ───────────────────────────────────────────────

class ConcreteTestScraper(BaseScraper):
    company_slug = "test-scraper"

    def fetch_company(self):
        return {
            "name": "Test Scraper",
            "website": "https://test.nl",
            "job_board_url": "https://test.nl/vacatures/",
            "scraper_class": "ConcreteTestScraper",
            "logo_url": "https://test.nl/logo.png",
            "description": "Test description",
        }

    def fetch_jobs(self):
        return []


class TestUpsertCompany:
    def test_inserts_new_company(self):
        scraper = ConcreteTestScraper()
        cur = MagicMock()
        cur.fetchone.side_effect = [None, (42,)]  # SELECT returns nothing, INSERT returns id=42
        company_id = scraper._upsert_company(cur, scraper.fetch_company())
        assert company_id == 42
        # First execute is SELECT, second is INSERT
        assert cur.execute.call_count == 2

    def test_updates_existing_company_when_logo_changed(self):
        scraper = ConcreteTestScraper()
        cur = MagicMock()
        cur.fetchone.return_value = (99, "https://test.nl/old-logo.png", "https://test.nl")
        company_id = scraper._upsert_company(cur, {
            "logo_url": "https://test.nl/new-logo.png",
            "website": "https://test.nl",
            "description": "",
        })
        assert company_id == 99
        assert cur.execute.call_count == 2  # SELECT + UPDATE

    def test_no_update_when_nothing_changed(self):
        scraper = ConcreteTestScraper()
        cur = MagicMock()
        cur.fetchone.return_value = (99, "https://test.nl/logo.png", "https://test.nl")
        company_id = scraper._upsert_company(cur, {
            "logo_url": "https://test.nl/logo.png",
            "website": "https://test.nl",
            "description": "",
        })
        assert company_id == 99
        assert cur.execute.call_count == 1  # Only SELECT, no UPDATE


# ── BaseScraper.run ───────────────────────────────────────────────────────────

class JobScraper(BaseScraper):
    """Concrete scraper with real jobs for testing run()."""
    company_slug = "test-job-scraper"

    def fetch_company(self):
        return {
            "name": "Test Job Scraper",
            "website": "https://test.nl",
            "job_board_url": "https://test.nl/vacatures/",
            "scraper_class": "JobScraper",
            "logo_url": "",
            "description": "",
        }

    def fetch_jobs(self):
        return [
            {
                "source_url": "https://test.nl/vacatures/pm-amsterdam/",
                "external_id": "pm-amsterdam",
                "title": "Pedagogisch Medewerker Amsterdam",
                "short_description": "We zoeken een PM.",
                "description": "We zoeken een PM voor 24-32 uur per week.",
                "location_name": "Amsterdam",
                "city": "Amsterdam",
                "postcode": "1012AB",
                "salary_min": 2200.0,
                "salary_max": 3000.0,
                "hours_min": 24,
                "hours_max": 32,
                "age_min": None,
                "age_max": None,
                "contract_type": "parttime",
                "job_type": "",
            }
        ]


def _make_conn(company_exists=False, company_id=42, current_urls=None, new_count=1):
    """
    Build a mock psycopg2 connection.
    geocode_locations is always patched separately in tests — so fetchall only
    handles the current_urls SELECT (one call).
    """
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur

    if company_exists:
        # _upsert_company: SELECT returns existing row; safety count
        cur.fetchone.side_effect = [
            (company_id, "", ""),   # company SELECT → (id, logo, website)
            (new_count,),           # safety COUNT(*)
        ]
    else:
        # _upsert_company: SELECT returns None, INSERT returns id; safety count
        cur.fetchone.side_effect = [
            None,                   # company SELECT → not found
            (company_id,),          # INSERT RETURNING id
            (new_count,),           # safety COUNT(*)
        ]

    # Only one fetchall call when geocode_locations is patched:
    # current active job URLs
    cur.fetchall.return_value = [(u,) for u in (current_urls or [])]
    return conn, cur


class TestBaseScrapeRun:
    def test_run_returns_skip_when_no_jobs(self):
        scraper = ConcreteTestScraper()  # fetch_jobs returns []
        result = scraper.run()
        assert result == {"inserted": 0, "updated": 0, "expired": 0, "skipped": True}

    def test_run_inserts_new_job(self):
        scraper = JobScraper()
        conn, cur = _make_conn(current_urls=set())

        with patch("scrapers.base.get_connection", return_value=conn):
            with patch("scrapers.base.geocode_locations", return_value={}):
                with patch("scrapers.vestigingen.match_vestiging", return_value=None):
                    result = scraper.run()

        assert result["inserted"] == 1
        assert result["updated"] == 0
        assert result["expired"] == 0

    def test_run_updates_existing_job(self):
        scraper = JobScraper()
        existing_url = "https://test.nl/vacatures/pm-amsterdam/"
        conn, cur = _make_conn(current_urls={existing_url})

        with patch("scrapers.base.get_connection", return_value=conn):
            with patch("scrapers.base.geocode_locations", return_value={}):
                with patch("scrapers.vestigingen.match_vestiging", return_value=None):
                    result = scraper.run()

        assert result["updated"] == 1
        assert result["inserted"] == 0

    def test_run_expires_removed_jobs(self):
        scraper = JobScraper()
        old_url = "https://test.nl/vacatures/old-job/"
        conn, cur = _make_conn(current_urls={old_url})

        with patch("scrapers.base.get_connection", return_value=conn):
            with patch("scrapers.base.geocode_locations", return_value={}):
                with patch("scrapers.vestigingen.match_vestiging", return_value=None):
                    result = scraper.run()

        assert result["expired"] == 1
        expire_calls = [c for c in cur.execute.call_args_list
                        if "is_expired = TRUE" in str(c)]
        assert len(expire_calls) == 1

    def test_run_raises_on_large_job_drop(self):
        """Safety check: rollback if active jobs drop > 30%."""
        scraper = JobScraper()
        # 20 current jobs, safety count returns 1 → 95% drop
        old_urls = {f"https://test.nl/vacatures/job-{i}/" for i in range(20)}
        conn, cur = _make_conn(current_urls=old_urls, new_count=1)

        with patch("scrapers.base.get_connection", return_value=conn):
            with patch("scrapers.base.geocode_locations", return_value={}):
                with patch("scrapers.vestigingen.match_vestiging", return_value=None):
                    with pytest.raises(ValueError, match="VEILIGHEID"):
                        scraper.run()

    def test_run_closes_connection_on_error(self):
        scraper = JobScraper()
        conn = MagicMock()
        conn.__enter__ = MagicMock(side_effect=Exception("DB down"))
        conn.__exit__ = MagicMock(return_value=False)

        with patch("scrapers.base.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB down"):
                scraper.run()
        conn.close.assert_called_once()

    def test_run_applies_geocode_to_city(self):
        scraper = JobScraper()
        conn, cur = _make_conn(current_urls=set())
        geo_cache = {"Amsterdam": {"city": "Amsterdam", "postcode": "1012AB",
                                   "lon": 4.895, "lat": 52.370, "municipality": "Amsterdam"}}

        with patch("scrapers.base.get_connection", return_value=conn):
            with patch("scrapers.base.geocode_locations", return_value=geo_cache):
                result = scraper.run()

        assert result["inserted"] == 1
        insert_calls = [c for c in cur.execute.call_args_list if "INSERT INTO jobs_job" in str(c)]
        assert len(insert_calls) == 1


# ── BaseScraper abstract methods ──────────────────────────────────────────────

class TestBaseScrapeAbstract:
    def test_fetch_company_raises(self):
        s = BaseScraper()
        with pytest.raises(NotImplementedError):
            s.fetch_company()

    def test_fetch_jobs_raises(self):
        s = BaseScraper()
        with pytest.raises(NotImplementedError):
            s.fetch_jobs()
