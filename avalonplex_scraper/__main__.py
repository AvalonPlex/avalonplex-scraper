import json
from argparse import ArgumentParser
from pathlib import Path

from avalonplex_core import XmlSerializer, normalize

from avalonplex_scraper.plugin import load_all_plugins
from avalonplex_scraper.utils import download_thumbnail


def main():
    parser = ArgumentParser(description="Avalon Plex Xml Scraper")
    parser.add_argument("runner", metavar="runner", type=str, help="runner")
    parser.add_argument("-o", "--output", metavar="output", default="", type=str, help="Output")
    parser.add_argument("-c", "--config", type=str, default="config.json", help="Config file")
    parser.add_argument("-p", "--scrapers_config", type=str, default="scrapers.json", help="Scrapers config file")
    parser.add_argument("-e", "--episode", type=int, help="Episode")
    parser.add_argument("-S", "--start", type=int, help="Start episode")
    parser.add_argument("-E", "--end", type=int, help="End episode")
    args = parser.parse_args()
    with open(args.scrapers_config, "r", encoding="utf-8") as file:
        scrapers_config = json.load(file)

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    factories, runners = load_all_plugins()

    runner = runners[args.runner]

    start = args.start
    end = args.end
    if start is None or end is None:
        start = args.episode
        end = args.episode
    if start is None or end is None:
        start = int(input("Enter start:"))
        end = int(input("Enter end:"))

    xml_serializer = XmlSerializer(ignore_blank=False, ignore_none=False, ignore_empty=False)

    for i in range(start, end + 1):
        episode, thumbnails = runner.run(i, scrapers_config)
        name = "{0} - s{1:02d}e{2:02d}".format(runner.series, runner.season, episode.episode)
        download_thumbnail(thumbnails, output.joinpath(name))
        if episode.title is not None:
            episode.title = normalize(episode.title)
        if episode.plot is not None:
            episode.plot = normalize(episode.plot)
        episode.writers = [normalize(w) for w in episode.writers]
        episode.directors = [normalize(w) for w in episode.directors]
        xml_serializer.serialize(episode, f"{name}.xml", output)


main()
