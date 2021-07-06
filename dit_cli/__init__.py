"""Set the CONFIG global and create tmp directory"""

from pathlib import Path

import pkg_resources

__version__ = pkg_resources.get_distribution("dit_cli").version
Path("/tmp/dit/").mkdir(parents=True, exist_ok=True)
