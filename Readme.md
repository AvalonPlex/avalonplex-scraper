# Avalon Plex Scraper

This is Python web scraper that uses for scraping website and generate XML files for [AvalonXmlAgent.bundle](https://github.com/joshuaavalon/AvalonXmlAgent.bundle).

This is **NOT** a plug-and-play solution. It require knowledge to Python and BeautifulSoup.

## Installation

```bash
git clone https://github.com/AvalonPlex/avalonplex-scraper.git
cd avalonplex-scraper
pip install requirements.txt
```

## Usage

First, you need to write a module or package and put it in `plugins`. There three main class `Runner`, `Scraper` and `ScraperFactory`.

### Runner

`Runner` uses one or more `Scraper` to gather information. It likes a task to be run. 
You **need** to extend your own `Runner` to specify which `Scraper` you are going to use.


```python
from typing import List

from avalonplex_scraper import Runner

class CustomRunner(Runner):
    def __init__(self):
        super().__init__("RunnerName", "SeriesName", 1)

    def _get_scraper_names(self) -> List[str]:
        return ["tvdb", "wiki", "constant", "html"]
```

`Scraper` is used to gather information from source. You probably need to extend or create your own `Scraper`.
For example, `TvDbScrapper` requires you to extend the class and pass the TVDB series id as argument.

`ScraperFactory` is used for creating `Scraper`.


## Support Scrapers

* TVDB
* Wikipedia
* Html
* Constant

### TVDB
TVDB scraper use its v2 API to acquire data. It requires API key which can get by creating a free account.


