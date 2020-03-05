"""Set the CONFIG global and create tmp directory"""

from pathlib import Path

from dit_cli.config import get_config

CONFIG = get_config()
Path(CONFIG['general']['tmp_dir']).mkdir(parents=True, exist_ok=True)
