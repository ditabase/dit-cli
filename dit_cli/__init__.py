"""Initialize, set the CONFIG global and create tmp directory"""

from pathlib import Path

from dit_cli.config import get_config

CONFIG = get_config()
Path(CONFIG['general']['tmp_dir']).mkdir(parents=True, exist_ok=True)


def traverse(item):
    """Generate every item in an arbitrary nested list,
    or just the item if it wasn't a list in the first place"""
    try:
        if isinstance(item, str):
            yield item
        else:
            for i in iter(item):
                for j in traverse(i):
                    yield j
    except TypeError:
        yield item
