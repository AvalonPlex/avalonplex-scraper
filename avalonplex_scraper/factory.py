import logging
from typing import Dict, List, Callable, Optional

from avalonplex_scraper.scraper import Scraper

logger = logging.getLogger(__name__)


class ScraperFactory:
    def get_available_scrapers(self) -> List[str]:
        raise NotImplementedError()

    def create_scraper_by_name(self, name: str, **kwargs) -> Scraper:
        raise NotImplementedError()

    def require_config(self, name: str) -> Optional[str]:
        raise NotImplementedError()


class SimpleScraperFactory(ScraperFactory):
    def __init__(self, mapping: Dict[str, Callable[[], Scraper]]):
        super().__init__()
        self._mapping = mapping

    def get_available_scrapers(self) -> List[str]:
        return list(self._mapping.keys())

    def create_scraper_by_name(self, name: str, **kwargs) -> Scraper:
        creator = self._mapping.get(name)
        if not callable(creator):
            raise NotImplementedError()
        return creator(**kwargs)

    def require_config(self, name: str) -> Optional[str]:
        creator = self._mapping.get(name)
        if issubclass(Scraper, creator):
            raise NotImplementedError()
        return creator.require_config()


__all__ = [ScraperFactory, SimpleScraperFactory]
