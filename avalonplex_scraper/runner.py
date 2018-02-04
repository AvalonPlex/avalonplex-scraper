import logging
from typing import Dict, List, Tuple, Any, Optional

from avalonplex_core import Episode

from avalonplex_scraper import ScraperFactory, Scraper
from avalonplex_scraper.utils import Cache

logger = logging.getLogger(__name__)


class Runner:
    def __init__(self, name: str, series: str, season: int):
        super().__init__()
        self._factories = {}
        self.name = name  # type: str
        self.series = series  # type: str
        self.season = season  # type: int

    def set_factories(self, factories: Dict[str, ScraperFactory]):
        self._factories = factories  # type: Dict[str, ScraperFactory]

    @Cache
    def _get_scraper_names(self) -> List[str]:
        raise NotImplementedError()

    def run(self, episode_num: int, config: Dict[str, Any]) -> Tuple[Episode, List[str]]:
        names = self._get_scraper_names()  # type:  List[str]
        scrapers = []  # type: List[Scraper]
        for name in names:
            factory = self._factories.get(name)  # type: ScraperFactory
            if factory is None:
                logger.error("%s is not a recognizable scraper name.", name)
                raise ValueError("Unrecognizable scraper name")
            factory_config = config.get(factory.require_config(name), {})
            scrapers.append(factory.create_scraper_by_name(name, **factory_config))
        if len(scrapers) <= 0:
            logging.warning("No scrapers is set.")
        episode = Episode()  # type: Episode
        thumbs = []  # type: List[str]
        for scraper in scrapers:
            scraper.process_episode(episode, episode_num)
            thumb = scraper.get_thumbnail(episode_num)
            if thumb is not None:
                thumbs.append(thumb)
        return episode, thumbs

    def get_output(self) -> str:
        return ""
