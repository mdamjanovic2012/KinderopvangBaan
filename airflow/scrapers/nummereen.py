"""Nummereen Kinderopvang — werkenbijnummereen.com (WordPress REST API: /wp-json/wp/v2/vacature)"""
from scrapers.wordpress_jobs import WordPressRestApiScraper


class NummereenScraper(WordPressRestApiScraper):
    company_slug      = "nummereen"
    company_name      = "Nummereen Kinderopvang"
    website_url       = "https://werkenbijnummereen.com"
    wp_rest_post_type = "vacature"
