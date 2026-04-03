"""Sport-BSO Flekss — flekss.nl (WordPress REST API: /wp-json/wp/v2/vacatures)"""
from scrapers.wordpress_jobs import WordPressRestApiScraper


class FlekssScraper(WordPressRestApiScraper):
    company_slug      = "flekss"
    company_name      = "Sport-BSO Flekss"
    website_url       = "https://flekss.nl"
    wp_rest_post_type = "vacatures"
