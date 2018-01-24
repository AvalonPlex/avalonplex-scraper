import json
# noinspection PyUnresolvedReferences
import re  # for exec
import traceback
from datetime import datetime
from time import sleep
from typing import Optional, Dict, Any, Callable, List

import requests
from avalonplex_core.model import Episode
# noinspection PyProtectedMember
from bs4 import BeautifulSoup, Tag
from selenium import webdriver


def table_to_2d(table_tag: Tag):
    rows = table_tag("tr")
    cols = rows[0](["td", "th"])
    table = [[None] * len(cols) for _ in range(len(rows))]
    for row_i, row in enumerate(rows):
        for col_i, col in enumerate(row(["td", "th"])):
            insert(table, row_i, col_i, col)
    return table


def insert(table, row, col, element):
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
        insert(table, row, col + 1, element)


class Scraper:
    def __init__(self, **kwarg):
        self.config = kwarg

    def process_episode(self, episode: Episode, episode_num: int):
        episode.episode = episode_num
        try:
            self._process_episode(episode, episode_num)
        except Exception as e:
            if self.config.get("catch", False):
                raise e
            else:
                print(traceback.format_exc())

    def _process_episode(self, episode: Episode, episode_num: int):
        raise NotImplementedError

    def get_thumbnail(self, episode_num: int) -> Optional[str]:
        return None


class WikiTableScraper(Scraper):
    """
    Support config

    url str: Wikipedia page url
    table int: No. of table to get. Default:0
    mapping Dict[str, int]: Table column mapping
    row str: Row number. Eval. Default: episode_num
    directors_split str: How to split entries. Eval. Default: lambda x: x.split()
    writers_split str: How to split entries. Eval. Default: lambda x: x.split()
    """
    Type = "wiki"  # type: str

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        table = kwargs.get("table", 0)
        response = requests.get(kwargs["url"])
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table", class_="wikitable")
        if not 0 <= table < len(tables):
            raise IndexError(f"There are only {len(tables)} table(s).")
        self.table = table_to_2d(tables[table])  # type: List[List[str]]
        self.mapping = kwargs.get("mapping", {})  # type: Dict[str, int]
        self.row = kwargs.get("row", "episode_num")  # type: str
        self.directors_split = kwargs.get("row", "lambda x: x.split()")  # type: str
        self.writers_split = kwargs.get("row", "lambda x: x.split()")  # type: str

    def _process_episode(self, episode: Episode, episode_num: int):
        row_i = eval(self.row)
        row = self.table[row_i]
        self._set_episode(episode, row, "title")
        episode.episode = episode_num
        self._set_episode(episode, row, "mpaa")
        self._set_episode(episode, row, "plot")
        self._set_episode(episode, row, "directors", eval(self.directors_split))
        self._set_episode(episode, row, "writers", eval(self.writers_split))
        self._set_episode(episode, row, "rating", float)

    def _set_episode(self, episode: Episode, row: List, key: str, converter: Optional[Callable[[Any], Any]] = str):
        mapping = self.mapping
        if key in mapping:
            data = row[mapping[key]]
            setattr(episode, key, converter(data))


class ConstantScraper(Scraper):
    """
    Support config

    Episode attr in global or episode attr in "episode" with number key attr
    """
    Type = "constant"  # type: str

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = kwargs  # type: Dict[str, Any]

    def _process_episode(self, episode: Episode, episode_num: int):
        for attr in [a for a in dir(episode) if not a.startswith("_")]:
            self._set_episode(episode, attr, episode_num)

    def _set_episode(self, episode: Episode, key: str, episode_num: int):
        episodes = self.config.get("episode", {})
        if episode_num in episodes and key in episodes[episode_num]:
            setattr(episode, key, episodes[episode_num][key])
        elif key in self.config:
            setattr(episode, key, self.config[key])


class TvDbScrapper(Scraper):
    """
    Support config

    id str: TVDB id.
    usage List[str]: Apply fields. Default: None (all)
    season str: Season number. Eval. Default: 1
    episode str: Episode number. Eval. Default: episode_num
    """
    Type = "tvdb"  # type: str

    def __init__(self, auth: Dict[str, str], **kwargs):
        super().__init__(**kwargs)
        self.config = kwargs  # type: Dict[str, Any]
        url = "https://api.thetvdb.com/login"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        response = requests.post(url, headers=headers, data=json.dumps(auth))
        token = json.loads(response.text)["token"]
        self.headers = {"Accept": "application/json", "Authorization": f"Bearer {token}", "Accept-Language": "ja"}
        url = f"https://api.thetvdb.com/series/{kwargs.get('id')}/episodes"
        self.episodes = json.loads(requests.get(url, headers=self.headers).text)["data"]
        self.usage = kwargs.get("usage")  # type: Optional[List[str]]
        self._cache = {}

    def _process_episode(self, episode: Episode, episode_num: int):
        json_result = self._load_episode(episode_num)
        if self.usage is None or "title" in self.usage:
            episode.title = json_result["episodeName"]
        if self.usage is None or "plot" in self.usage:
            episode.plot = json_result["overview"]
        if self.usage is None or "aired" in self.usage:
            try:
                episode.aired = datetime.strptime(json_result["firstAired"], "%Y-%m-%d").date()
            except ValueError:
                episode.aired = None

    def get_thumbnail(self, episode_num: int) -> Optional[str]:
        json_result = self._load_episode(episode_num)
        thumbnail = json_result["filename"]
        if not thumbnail.isspace():
            return f"https://www.thetvdb.com/banners/{thumbnail}"
        return None

    def _load_episode(self, episode_num: int):
        season = eval(self.config.get("season", "1"))
        episode_num = eval(self.config.get("episode", "episode_num"))
        ep = next(e for e in self.episodes if e["airedSeason"] == season and e["airedEpisodeNumber"] == episode_num)
        ep_id = ep["id"]
        if ep_id not in self._cache:
            url = f"https://api.thetvdb.com/episodes/{ep_id}"
            response = requests.get(url, headers=self.headers)
            self._cache[ep_id] = json.loads(response.text)["data"]
        return self._cache[ep_id]


class HtmlScraper(Scraper):
    Type = "html"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.url_eval = kwargs["url"]  # type: str
        self._cache = {}  # type: Dict[str, BeautifulSoup]
        self._use_selenium = kwargs.get("selenium", False)  # type: bool
        self.config = kwargs

    def _process_episode(self, episode: Episode, episode_num: int):
        soup = self._load_html(episode_num)
        for attr in [a for a in dir(episode) if not a.startswith("_")]:
            self._set_episode(episode, attr, episode_num, soup)

    def get_thumbnail(self, episode_num: int) -> Optional[str]:
        soup = self._load_html(episode_num)
        selector = self._get_selector("thumbnail", episode_num)
        if selector is None:
            return None
        value = None
        local = locals()
        for command in selector:
            exec(command, globals(), local)
        return local.get("value", value)

    def _set_episode(self, episode: Episode, key: str, episode_num: int, soup: BeautifulSoup):
        selector = self._get_selector(key, episode_num)
        if selector is None:
            return
        value = None
        local = locals()
        for command in selector:
            exec(command, globals(), local)
        value = local.get("value", value)
        setattr(episode, key, value)

    def _get_selector(self, key: str, episode_num: int) -> Optional[Dict[str, str]]:
        selectors = self.config.get("selector", {})
        if episode_num in selectors and key in selectors[episode_num]:
            return selectors[episode_num][key]
        elif key in self.config:
            return self.config[key]
        else:
            return None

    def _load_html(self, episode_num: int) -> BeautifulSoup:
        url = eval(self.url_eval)
        if url not in self._cache:
            if self._use_selenium:
                driver = webdriver.Firefox()
                driver.get(url)
                sleep(1)
                html = driver.page_source
            else:
                response = requests.get(url)
                html = response.text
            soup = BeautifulSoup(html, "html5lib")
            self._cache[url] = soup
        return self._cache[url]
