## Example config

**config.json**

```json
{
  "auth": {
    "tvdb": {
      "apikey": "",
      "userkey": "",
      "username": ""
    }
  },
  "series": {
    "asd": {
      "name": "11eyes",
      "season": 1,
      "output": "output",
      "scraper": [
        {
          "type": "tvdb",
          "id": "117851"
        },
        {
          "type": "wiki",
          "url": "https://ja.wikipedia.org/wiki/11eyes_-罪と罰と贖いの少女-",
          "table": 0,
          "mapping": {
            "writers": 2
          }
        },
        {
          "type": "constant",
          "directors": [
            "下田正美"
          ]
        },
        {
          "type": "html",
          "catch": true,
          "url": "'http://gabdro.com/story{0:02d}.html'.format(episode_num)",
          "title": [
            "value = soup.find('div', class_='storyInner').find('h2').get_text()",
            "g = re.search('.*「(.*)」', value, re.IGNORECASE)",
            "value = g.group(1)"
          ]
        }
      ]
    }
  }
}
```