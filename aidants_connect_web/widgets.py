from copy import deepcopy

from aidants_connect_common.widgets import DetailedRadioSelect


class MandatDureeRadioSelect(DetailedRadioSelect):
    option_template_name = "widgets/mandat-duree-radio-option.html"
    container_classes = "grid"
    input_wrapper_classes = "tile"
    label_classes = "shadowed"


class MandatDemarcheSelect(DetailedRadioSelect):
    allow_multiple_selected = True
    input_type = "checkbox"
    option_template_name = "widgets/mandat-demarche-checkbox.html"
    container_classes = "grid grid-4"
    input_wrapper_classes = "tile"
    label_classes = "shadowed"
    checkbox_select_multiple = True

    @staticmethod
    def choices_label_adapter(label: dict) -> dict:
        result = deepcopy(label)
        result["img_src"] = result.pop("icon")
        result["label"] = result.pop("titre")
        return result
