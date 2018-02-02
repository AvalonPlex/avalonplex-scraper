from avalonplex_scraper import SimpleScraperFactory
from plugins.default.scraper import ConstantScraper, WikiTableScraper, TvDbScrapper, HtmlScraper

__all__ = [ConstantScraper, WikiTableScraper, TvDbScrapper, HtmlScraper]


class Factory(SimpleScraperFactory):
    def __init__(self):
        super().__init__({
            "constant": ConstantScraper,
            "wiki": WikiTableScraper,
            "tvdb": TvDbScrapper,
            "html": HtmlScraper
        })
