"""
KION Kinderopvang scraper — werkenbijkion.nl

Platform: Recruitee ATS (company ID 51130).
Jobs fetched from public Recruitee API, no scraping of HTML needed.
"""

from scrapers.recruitee_api import RecruiteeAPIScraper


class KIONScraper(RecruiteeAPIScraper):
    company_slug  = "kion"
    company_name  = "KION Kinderopvang"
    recruitee_id  = 51130
    website_url   = "https://werkenbijkion.nl"
    job_board_url = "https://werkenbijkion.nl/vacaturepagina"
