import json
from datetime import datetime
from time import sleep
from typing import Optional, Dict, Any, Callable, List, TypeVar

import requests
from avalonplex_core.model import Episode
# noinspection PyProtectedMember
from bs4 import BeautifulSoup, Tag
from selenium import webdriver

from avalonplex_scraper import Scraper, Cache
from avalonplex_scraper.utils import table_to_2d

T = TypeVar("T")


def _default_if_none(value: Optional[T], default: T) -> T:
    return value if value is not None else default


def _table_to_2d(table_tag: Tag):
    rows = table_tag("tr")
    cols = rows[0](["td", "th"])
    table = [[None] * len(cols) for _ in range(len(rows))]
    for row_i, row in enumerate(rows):
        for col_i, col in enumerate(row(["td", "th"])):
            _insert(table, row_i, col_i, col)
    return table


def _insert(table, row, col, element):
    if row >= len(table) or col >= len(table[row]):
        return
    if table[row][col] is None:
        value = element.get_text()
        table[row][col] = value
        if element.has_attr("colspan"):
            span = int(element["colspan"])
            for i in range(1, span):
                table[row][col + i] = value
        if element.has_attr("rowspan"):
            span = int(element["rowspan"])
            for i in range(1, span):
                table[row + i][col] = value
    else:
        _insert(table, row, col + 1, element)


class ConstantScraper(Scraper):
    def __init__(self, global_constant: Dict[str, Any] = None, episode_constant: Dict[int, Dict[str, Any]] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self._global_constant = _default_if_none(global_constant, {})  # type: Dict[str, Any]
        self._episode_constant = _default_if_none(episode_constant, {})  # type: Dict[int, Dict[str, Any]]

    def _process_episode(self, episode: Episode, episode_num: int):
        for attr in [a for a in dir(episode) if not a.startswith("_")]:
            self._set_episode(episode, attr, episode_num)

    def _set_episode(self, episode: Episode, key: str, episode_num: int):
        if episode_num in self._episode_constant and key in self._episode_constant[episode_num]:
            setattr(episode, key, self._episode_constant[episode_num][key])
        elif key in self._global_constant:
            setattr(episode, key, self._global_constant[key])


class WikiTableScraper(Scraper):
    """
    url str: Wikipedia page url
    table int: No. of table to get. Default:0
    mapping Dict[str, int]: Table column mapping

    Override _get_row_num, _parse_directors, _parse_writers
    """

    def __init__(self, url: str, table: int = 0, mapping: Dict[str, int] = None, **kwargs):
        super().__init__(**kwargs)
        response = requests.get(url)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table", class_="wikitable")
        if not 0 <= table < len(tables):
            raise IndexError(f"There are only {len(tables)} table(s).")
        self.table = table_to_2d(tables[table])  # type: List[List[str]]
        self.mapping = _default_if_none(mapping, {})  # type: Dict[str, int]

    def _process_episode(self, episode: Episode, episode_num: int):
        row_i = self._get_row_num(episode_num)
        row = self.table[row_i]
        self._set_episode(episode, row, "title")
        episode.episode = episode_num
        self._set_episode(episode, row, "mpaa")
        self._set_episode(episode, row, "plot")
        self._set_episode(episode, row, "directors", self._parse_directors)
        self._set_episode(episode, row, "writers", self._parse_writers)
        self._set_episode(episode, row, "rating", float)

    def _get_row_num(self, episode_num: int) -> int:
        return episode_num

    def _parse_directors(self, value: str) -> List[str]:
        return value.split()

    def _parse_writers(self, value: str) -> List[str]:
        return value.split()

    def _set_episode(self, episode: Episode, row: List, key: str, converter: Optional[Callable[[Any], Any]] = str):
        mapping = self.mapping
        if key in mapping:
            data = row[mapping[key]]
            setattr(episode, key, converter(data))


class TvDbScrapper(Scraper):
    """
    Support config

    id str: TVDB id.
    usage List[str]: Apply fields. Default: None (all)
    """

    def __init__(self, tvdb_id: str, api_key: str, user_key: str, user_name: str, usage: Optional[List[str]] = None,
                 **kwargs):
        super().__init__(**kwargs)
        url = "https://api.thetvdb.com/login"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        data = {
            "apikey": api_key,
            "userkey": user_key,
            "username": user_name
        }
        response = requests.post(url, headers=headers, data=json.dumps(data))
        token = json.loads(response.text)["token"]
        self.headers = {"Accept": "application/json", "Authorization": f"Bearer {token}", "Accept-Language": "ja"}
        url = f"https://api.thetvdb.com/series/{tvdb_id}/episodes"
        self.episodes = json.loads(requests.get(url, headers=self.headers).text)["data"]
        self._usage = usage  # type: Optional[List[str]]

    def _process_episode(self, episode: Episode, episode_num: int):
        json_result = self._load_episode(episode_num)
        if self._usage is None or "title" in self._usage:
            episode.title = json_result["episodeName"]
        if self._usage is None or "plot" in self._usage:
            episode.plot = json_result["overview"]
        if self._usage is None or "aired" in self._usage:
            try:
                episode.aired = datetime.strptime(json_result["firstAired"], "%Y-%m-%d").date()
            except ValueError:
                episode.aired = None

    @Cache
    def _get_thumbnail(self, episode_num: int) -> Optional[str]:
        json_result = self._load_episode(episode_num)
        thumbnail = json_result["filename"]
        if not thumbnail.isspace() and (self._usage is None or "thumbnail" in self._usage):
            return f"https://www.thetvdb.com/banners/{thumbnail}"
        return None

    def _get_season_number(self, episode_num: int) -> int:
        return 1

    def _get_episode_number(self, episode_num: int) -> int:
        return episode_num

    @Cache
    def _load_episode(self, episode_num: int) -> Dict[str, Any]:
        season = self._get_season_number(episode_num)
        episode_num = self._get_episode_number(episode_num)
        ep = next(e for e in self.episodes if e["airedSeason"] == season and e["airedEpisodeNumber"] == episode_num)
        ep_id = ep["id"]
        url = f"https://api.thetvdb.com/episodes/{ep_id}"
        response = requests.get(url, headers=self.headers)
        return json.loads(response.text)["data"]


class HtmlScraper(Scraper):
    def __init__(self, use_selenium: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._use_selenium = use_selenium  # type: bool

    def _process_episode(self, episode: Episode, episode_num: int):
        soup = self._load_html(episode_num)
        self._parse_episode(episode, episode_num, soup)

    def _get_thumbnail(self, episode_num: int) -> Optional[str]:
        soup = self._load_html(episode_num)
        return self._parse_thumbnail(episode_num, soup)

    @Cache
    def _load_html(self, episode_num: int) -> BeautifulSoup:
        url = self._get_url(episode_num)
        if self._use_selenium:
            driver = webdriver.Firefox()
            driver.get(url)
            sleep(1)
            html = driver.page_source
        else:
            response = requests.get(url)
            html = response.text
        return BeautifulSoup(html, "html5lib")

    @Cache
    def _get_url(self, episode_num: int) -> str:
        raise NotImplementedError()

    @Cache
    def _parse_thumbnail(self, episode_num: int, soup: BeautifulSoup) -> Optional[str]:
        return None

    def _parse_episode(self, episode: Episode, episode_num: int, soup: BeautifulSoup):
        pass
