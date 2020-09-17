"""Set the CONFIG global and create tmp directory"""

from pathlib import Path

import pkg_resources
from dit_cli.config import get_config

__version__ = pkg_resources.get_distribution("dit_cli").version
CONFIG = get_config()
Path(CONFIG["general"]["tmp_dir"]).mkdir(parents=True, exist_ok=True)
