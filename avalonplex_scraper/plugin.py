import inspect
import logging
from importlib import import_module
from pathlib import Path
from typing import Dict, Tuple, Iterable

from avalonplex_scraper.factory import ScraperFactory
from avalonplex_scraper.runner import Runner

logger = logging.getLogger(__name__)


class PluginLoader:
    _folder = "plugins"

    def __init__(self):
        self._modules = []
        for path in Path(self._folder).iterdir():
            module_name = None
            if path.is_file() and path.suffix == ".py":
                module_name = f"plugins.{path.name[:-3]}"
            if path.is_dir() and not path.name.startswith("_") and not path.name.startswith(".") and \
                    path.joinpath("__init__.py").is_file():
                module_name = f"plugins.{path.name}"
            if module_name is not None:
                imported_module = import_module(module_name)
                self._modules.append(imported_module)

    def get_classes(self, base) -> Iterable:
        for module in self._modules:
            for cls_name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and obj.__module__.startswith(f"{self._folder}.") and issubclass(obj, base):
                    yield obj


def load_all_plugins() -> Tuple[Dict[str, ScraperFactory], Dict[str, Runner]]:
    loader = PluginLoader()

    factories = {}  # type: Dict[str, ScraperFactory]
    for cls in loader.get_classes(ScraperFactory):
        factory = cls()  # type: ScraperFactory
        for name in factory.get_available_scrapers():
            if name not in factories:
                factories[name] = factory
            else:
                logger.warning("%s cannot register %s because it is already registered by %s",
                               type(factory).__name__, name, type(factories[name]).__name__)

    runners = {}  # type: Dict[str, Runner]
    for cls in loader.get_classes(Runner):
        runner = cls()  # type: Runner
        name = runner.name
        if name not in runners:
            runner.set_factories(factories)
            runners[name] = runner
        else:
            logger.warning("%s cannot register %s because it is already registered by %s",
                           type(runner).__name__, name, type(runners[name]).__name__)
    return factories, runners


__all__ = [load_all_plugins]
