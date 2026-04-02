"""Unit tests for Kinderwoud scraper (WordPress with JSON-LD)."""
import json, sys, os, pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scrapers.kinderwoud import KinderwoudScraper

JOBPOSTING_LD = {
    "@context": "https://schema.org/",
    "@type": "JobPosting",
    "title": "Pedagogisch Medewerker",
    "identifier": {"@type": "PropertyValue", "value": "pm-12345"},
    "jobLocation": [{"@type": "Place", "address": {
        "@type": "PostalAddress",
        "addressLocality": "Amsterdam",
        "postalCode": "1011AB",
    }}],
    "baseSalary": {
        "@type": "MonetaryAmount",
        "value": {"@type": "QuantitativeValue", "minValue": 2200, "maxValue": 3000},
    },
    "employmentType": ["PART_TIME"],
    "description": "<p>We zoeken een PM voor 24-32 uur per week.</p>",
}

LISTING_HTML = """<html><body>
<a href="/vacatures/pedagogisch-medewerker-amsterdam/">PM Amsterdam</a>
<a href="/vacatures/groepsleider-bso-haarlem/">GL BSO Haarlem</a>
<a href="/vacatures/">Alle vacatures</a>
</body></html>"""

DETAIL_HTML = f"""<html><body>
<h1>Pedagogisch Medewerker</h1>
<script type="application/ld+json">{json.dumps(JOBPOSTING_LD)}</script>
</body></html>"""


class TestKinderwoudConfig:
    def test_company_slug(self): assert KinderwoudScraper.company_slug == "kinderwoud"
    def test_listing_url(self): assert "werkenbijkinderwoud.nl" in KinderwoudScraper.listing_url


class TestKinderwoudFetchJobs:
    def test_parses_jsonld(self):
        scraper = KinderwoudScraper()
        listing_r = MagicMock(); listing_r.text = LISTING_HTML; listing_r.raise_for_status = MagicMock()
        detail_r = MagicMock(); detail_r.text = DETAIL_HTML; detail_r.raise_for_status = MagicMock()
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=[listing_r, detail_r, detail_r]):
            jobs = scraper.fetch_jobs()
        assert len(jobs) == 2
        assert jobs[0]["title"] == "Pedagogisch Medewerker"
        assert jobs[0]["city"] == "Amsterdam"
        assert jobs[0]["salary_min"] == 2200.0

    def test_empty_on_error(self):
        with patch("scrapers.wordpress_jobs.requests.get", side_effect=Exception("err")):
            assert KinderwoudScraper().fetch_jobs() == []


@pytest.mark.integration
class TestKinderwoudLive:
    def test_listing_bereikbaar(self):
        import requests
        assert requests.get(KinderwoudScraper.listing_url, timeout=15).status_code == 200
