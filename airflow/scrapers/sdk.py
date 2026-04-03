"""SDK Kinderopvang — https://sdk-kinderopvang.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class SdkScraper(WordPressJobsScraper):
    company_slug     = "sdk"
    company_name     = "SDK Kinderopvang"
    listing_url      = "https://sdk-kinderopvang.nl/vacatures/"
    website_url      = "https://sdk-kinderopvang.nl"
    job_url_contains = "/vacatures/"
