from .base import Converter


class EmuelecConverter(Converter):
    key = "emuelec"
    label = "EmuELEC (gamelist.xml)"

    def import_from(self, src, con):
        raise NotImplementedError("TODO")
