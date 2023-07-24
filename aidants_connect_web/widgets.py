from copy import deepcopy

from aidants_connect_common.widgets import DetailedRadioSelect


class MandatDureeRadioSelect(DetailedRadioSelect):
    option_template_name = "widgets/mandat-duree-radio-option.html"
    container_classes = "grid"
    label_classes = "shadowed"
    input_wrapper_classes = "mandat-duree"


class MandatDemarcheSelect(DetailedRadioSelect):
    allow_multiple_selected = True
    input_type = "checkbox"
    input_wrapper_classes = "mandat-demarche"
    option_template_name = "widgets/mandat-demarche-checkbox.html"
    container_classes = "grid grid-4"
    label_classes = "shadowed"
    checkbox_select_multiple = True

    @staticmethod
    def choices_label_adapter(label: dict) -> dict:
        result = deepcopy(label)
        result["img_src"] = result.pop("icon")
        result["label"] = result.pop("titre")
        return result
