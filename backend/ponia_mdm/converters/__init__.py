from .base import Converter
from .pegasus import PegasusConverter
from .emuelec import EmuelecConverter
from .folder import FolderConverter

CONVERTERS = {c.key: c for c in (PegasusConverter, EmuelecConverter, FolderConverter)}
__all__ = ["Converter", "CONVERTERS"]
