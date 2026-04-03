"""Forte Kinderopvang — werkenbijforte.nl (WordPress REST API: /wp-json/wp/v2/vacature)"""
from scrapers.wordpress_jobs import WordPressRestApiScraper


class ForteScraper(WordPressRestApiScraper):
    company_slug      = "forte"
    company_name      = "Forte Kinderopvang"
    website_url       = "https://werkenbijforte.nl"
    wp_rest_post_type = "vacature"
