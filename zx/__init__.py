"""Zintellix Semantic Layer — POC reference implementation.

Thirteen layers, each in its own module, each built in its thinnest honest form.
The seams between modules are the deliverable: they are the promotion path to SL-0.
"""

__version__ = "0.1.0"
ONTOLOGY_VERSION = "0.1.0"
WORKSPACE_ID = "ws1"

from . import config  # noqa: E402,F401 — loads .env + forces UTF-8 stdout on import
