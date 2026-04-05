"""Junis Kinderopvang — werkenbijjunis.nl (WordPress REST API: /wp-json/wp/v2/vacatures)"""
from scrapers.wordpress_jobs import WordPressRestApiScraper


class JunisScraper(WordPressRestApiScraper):
    company_slug      = "junis"
    company_name      = "Junis Kinderopvang"
    website_url       = "https://werkenbijjunis.nl"
    wp_rest_post_type = "vacatures"
