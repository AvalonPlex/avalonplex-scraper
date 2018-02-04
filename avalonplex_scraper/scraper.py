import traceback
from typing import Optional

from avalonplex_core.model import Episode


class Scraper:
    def __init__(self, catch: bool = False):
        self._catch = catch  # type: Optional[bool]

    def process_episode(self, episode: Episode, episode_num: int):
        episode.episode = episode_num
        try:
            self._process_episode(episode, episode_num)
        except Exception as e:
            if self._catch:
                print(traceback.format_exc())
            else:
                raise e

    def _process_episode(self, episode: Episode, episode_num: int):
        raise NotImplementedError

    def get_thumbnail(self, episode_num: int) -> Optional[str]:
        try:
            return self._get_thumbnail(episode_num)
        except Exception as e:
            if self._catch:
                print(traceback.format_exc())
                return None
            else:
                raise e

    def _get_thumbnail(self, episode_num: int) -> Optional[str]:
        return None

    @staticmethod
    def require_config() -> Optional[str]:
        return None


__all__ = [Scraper]
