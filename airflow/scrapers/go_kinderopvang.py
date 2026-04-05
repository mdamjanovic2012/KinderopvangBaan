"""
GO! Kinderopvang scraper — werkenbij.go-kinderopvang.nl

Platform: WordPress Jobs
URL pattern: /vacature/
"""

from scrapers.wordpress_jobs import WordPressJobsScraper


class GoKinderopvangScraper(WordPressJobsScraper):
    company_slug     = "go-kinderopvang"
    company_name     = "GO! Kinderopvang"
    listing_url      = "https://werkenbij.go-kinderopvang.nl/vacature/"
    website_url      = "https://werkenbij.go-kinderopvang.nl"
    job_url_contains = "/vacature/"
