from .base import Converter


class FolderConverter(Converter):
    key = "folder"
    label = 自訂資料夾

    def import_from(self, src, con):
        raise NotImplementedError("TODO")
