"""Kinderopvang Purmerend — kinderopvangpurmerend.nl (WordPress REST API: /wp-json/wp/v2/vacatures)"""
from scrapers.wordpress_jobs import WordPressRestApiScraper


class KoPurmerendScraper(WordPressRestApiScraper):
    company_slug      = "ko-purmerend"
    company_name      = "Kinderopvang Purmerend"
    website_url       = "https://kinderopvangpurmerend.nl"
    wp_rest_post_type = "vacatures"
