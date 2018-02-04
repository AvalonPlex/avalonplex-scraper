import re
from typing import List

from avalonplex_core import Episode
from bs4 import BeautifulSoup

import avalonplex_scraper
from plugins import default


class TvDbScraper(default.TvDbScrapper):
    def __init__(self, **kwargs):
        super().__init__("117851", **kwargs)


class WikiTableScraper(default.WikiTableScraper):
    def __init__(self, **kwargs):
        super().__init__("https://ja.wikipedia.org/wiki/11eyes_-罪と罰と贖いの少女-", mapping={"writers": 2}, **kwargs)


class ConstantScraper(default.ConstantScraper):
    def __init__(self, **kwargs):
        super().__init__({"directors": ["下田正美"]}, **kwargs)


class HtmlScraper(default.HtmlScraper):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _get_url(self, episode_num: int):
        return "http://gabdro.com/story{0:02d}.html".format(episode_num)

    def _parse_episode(self, episode: Episode, episode_num: int, soup: BeautifulSoup):
        value = soup.find("div", class_="storyInner").find("h2").get_text()
        g = re.search(".*「(.*)」", value, re.IGNORECASE)
        episode.title = g.group(1)


class Factory(avalonplex_scraper.SimpleScraperFactory):
    def __init__(self):
        super().__init__({
            "11eyes.tvdb": TvDbScraper,
            "11eyes.wiki": WikiTableScraper,
            "11eyes.constant": ConstantScraper,
            "11eyes.html": HtmlScraper
        })


class Runner(avalonplex_scraper.Runner):
    def __init__(self):
        super().__init__("11eyes", "11eyes", 1)

    def _get_scraper_names(self) -> List[str]:
        return ["11eyes.tvdb", "11eyes.wiki", "11eyes.constant", "11eyes.html"]
