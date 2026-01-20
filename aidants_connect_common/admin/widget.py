from import_export.widgets import BooleanWidget


class ZRRBooleanWidget(BooleanWidget):
    def __init__(self) -> None:
        self.commune_zrr_classification = None
        super().__init__()

    def clean(self, value, row=None, **kwargs):
        if self.commune_zrr_classification is None:
            return None
        return value == self.commune_zrr_classification
