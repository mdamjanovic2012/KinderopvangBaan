"""
Rastergroep scraper — werkenbijrastergroep.recruitee.com

Platform: Recruitee (API bevestigd op 2026-04-03)
Company ID: 106368  (gevonden via window.recruitee.customIntegrationsApi op de careers pagina)
API: https://api.recruitee.com/c/106368/careers/offers?lang=nl
"""

from scrapers.recruitee_api import RecruiteeAPIScraper


class RastergroepScraper(RecruiteeAPIScraper):
    company_slug  = "rastergroep"
    company_name  = "Rastergroep"
    recruitee_id  = 106368
    website_url   = "https://www.rastergroep.nl"
    job_board_url = "https://werkenbijrastergroep.recruitee.com"
