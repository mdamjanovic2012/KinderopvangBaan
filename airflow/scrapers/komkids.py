"""KomKids — https://werkenbij.komkids.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class KomKidsScraper(WordPressJobsScraper):
    company_slug     = "komkids"
    company_name     = "KomKids"
    listing_url      = "https://werkenbij.komkids.nl/vacatures/"
    website_url      = "https://werkenbij.komkids.nl"
    job_url_contains = "/vacatures/"
