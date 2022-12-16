from django.forms import RadioSelect


class DetailedRadioSelect(RadioSelect):
    template_name = "widgets/detailed_radio.html"
    option_template_name = "widgets/detailed_radio_option.html"
    input_wrapper_base_class = "detailed-radio-select"

    def __init__(self, attrs=None, choices=(), wrap_label=False):
        """Unwrap label by default and set a CSS class"""
        self.wrap_label = wrap_label
        attrs = attrs or {}
        self._input_wrapper_classes = attrs.pop(
            "input_wrapper_classes", self.input_wrapper_base_class
        )
        self._container_class = attrs.pop("input_wrapper_classes", "")
        super().__init__(attrs, choices)

    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        opts_context = super().create_option(
            name, value, label, selected, index, subindex, attrs
        )

        if isinstance(opts_context["label"], dict):
            opts_context.update(**opts_context.pop("label"))

        opts_context["wrap_label"] = self.wrap_label
        opts_context["container_class"] = self.container_classes(self._container_class)
        opts_context["input_wrapper_base_class"] = self.input_wrapper_base_class
        opts_context["input_wrapper_classes"] = self.input_wrapper_classes(
            self._input_wrapper_classes
        )

        if "id" in attrs:
            opts_context["attrs"]["id"] = self.id_for_label(
                attrs["id"], str(value).lower() if value else index
            )

        return opts_context

    def input_wrapper_classes(self, extra_classes=None):
        extra_classes = str(extra_classes) if extra_classes else ""
        return " ".join([self.input_wrapper_base_class, *extra_classes.split(" ")])

    def container_classes(self, extra_classes=None):
        if not extra_classes:
            return ""
        return " ".join([*extra_classes.split(" ")])
