from copy import deepcopy

from aidants_connect_common.widgets import DetailedRadioSelect


class MandatDureeRadioSelect(DetailedRadioSelect):
    container_classes = "fr-grid-row fr-grid-row--gutters"
    label_classes = "shadowed"
    input_wrapper_classes = "mandat-duree fr-col-12 fr-col-md-6"
    option_tile_classes = "fr-radio-group"
    hide_group_label = True


class MandatDemarcheSelect(DetailedRadioSelect):
    allow_multiple_selected = True
    input_type = "checkbox"
    input_wrapper_classes = "mandat-demarche fr-col-12 fr-col-md-6 fr-col-xl-3"
    hide_group_label = True
    option_template_name = "widgets/mandat-demarche-checkbox.html"
    container_classes = "fr-grid-row fr-grid-row--gutters"
    label_classes = ""
    checkbox_select_multiple = True

    @staticmethod
    def choices_label_adapter(label: dict) -> dict:
        result = deepcopy(label)
        result["img_src"] = result.pop("icon")
        result["label"] = result.pop("titre")
        return result
