import json
import mimetypes
from argparse import ArgumentParser
from os import path
from typing import List

import requests
from PIL import Image
from avalonplex_core.model import Episode
from avalonplex_core.serialize import XmlSerializer

from avalonplex_scraper.scraper import WikiTableScraper, ConstantScraper, TvDbScrapper, Scraper, HtmlScraper


def main():
    parser = ArgumentParser(description="Avalon Plex Xml Scraper")
    parser.add_argument("-s", "--series", metavar="series", type=str, help="Series name")
    parser.add_argument("-c", "--config", type=str, default="config.json", help="Config file")
    parser.add_argument("-e", "--episode", type=int, help="Episode")
    parser.add_argument("-S", "--start", type=int, help="Start episode")
    parser.add_argument("-E", "--end", type=int, help="End episode")
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as file:
        config = json.load(file)
    series = config.get("series")
    if series is None:
        raise ValueError("Missing series in config.")
    series_code = args.series
    if series_code is None:
        series_code = input("Enter series code:")
    series_config = series.get(series_code)
    if series_config is None:
        raise ValueError("Missing series name.")

    start = args.start
    end = args.end
    if start is None or end is None:
        start = args.episode
        end = args.episode
    if start is None or end is None:
        start = int(input("Enter start:"))
        end = int(input("Enter end:"))

    scraper_configs = series_config.get("scraper", [])
    scrapers = []
    for scraper_config in scraper_configs:
        scraper_type = scraper_config.get("type")
        if scraper_type == WikiTableScraper.Type:
            scrapers.append(WikiTableScraper(**scraper_config))
        elif scraper_type == ConstantScraper.Type:
            scrapers.append(ConstantScraper(**scraper_config))
        elif scraper_type == TvDbScrapper.Type:
            tvdb_auth = config["auth"][TvDbScrapper.Type]
            s = TvDbScrapper(tvdb_auth, **scraper_config)
            scrapers.append(s)
        elif scraper_type == HtmlScraper.Type:
            scrapers.append(HtmlScraper(**scraper_config))
    name = series_config.get("name")
    season = series_config.get("season")
    output = series_config.get("output", "")

    episodes = []
    for i in range(start, end + 1):
        episode = scrap_episode(i, output, scrapers, name, season)
        episodes.append(episode)
    xml_serializer = XmlSerializer(ignore_blank=False, ignore_none=False, ignore_empty=False)
    for e in episodes:
        xml_serializer.serialize(e, "{0} - s{1:02d}e{2:02d}.xml".format(name, season, e.episode), output)


def scrap_episode(episode_num: int, output: str, scrapers: List[Scraper], name: str, season: int) -> Episode:
    episode = Episode()
    download_thumb = True
    for scraper in scrapers:
        if download_thumb:
            thumbnail_name = "{0} - s{1:02d}e{2:02d}".format(name, season, episode_num)
            thumbnail_path = path.join(output, thumbnail_name)
            thumbnail = scraper.get_thumbnail(episode_num)
            if thumbnail is not None:
                response = requests.get(thumbnail, stream=True)
                if response.status_code == 200:
                    content_type = response.headers.get("content-type")
                    ext = None
                    if content_type is not None:
                        ext = mimetypes.guess_extension(content_type)
                        if ext in [".jpe", ".jpeg"]:
                            ext = ".jpg"
                    if ext is None:
                        ext = ".png"
                    thumbnail_path += ext
                    image = Image.open(response.raw)  # type: Image
                    image.save(thumbnail_path)
                    download_thumb = False
        scraper.process_episode(episode, episode_num)
    return episode


main()
