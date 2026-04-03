"""KomKids — werkenbij.komkids.nl (WordPress REST API: /wp-json/wp/v2/vacatures)"""
from scrapers.wordpress_jobs import WordPressRestApiScraper


class KomKidsScraper(WordPressRestApiScraper):
    company_slug      = "komkids"
    company_name      = "KomKids"
    website_url       = "https://werkenbij.komkids.nl"
    wp_rest_post_type = "vacatures"
