"""Kinderopvang Roermond — kinderopvangroermond.nl"""
from scrapers.wordpress_jobs import WordPressJobsScraper


class KinderopvangRoermondScraper(WordPressJobsScraper):
    company_slug     = "kinderopvang-roermond"
    company_name     = "Kinderopvang Roermond"
    listing_url      = "https://www.kinderopvangroermond.nl/werken-bij/"
    website_url      = "https://www.kinderopvangroermond.nl"
    job_url_contains = "/vacature/"
