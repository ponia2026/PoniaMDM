from .base import Converter


class PegasusConverter(Converter):
    key = "pegasus"
    label = Pegasus (跳坑者聯盟)

    def import_from(self, src, con):
        raise NotImplementedError("TODO")
