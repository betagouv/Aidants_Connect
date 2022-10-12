from django.forms import RadioSelect


class DetailedRadioSelect(RadioSelect):
    template_name = "widgets/detailed_radio_select.html"

    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        opts_context = super().create_option(
            name, value, label, selected, index, subindex, attrs
        )

        if isinstance(opts_context["label"], dict):
            opts_context["label"], description = opts_context["label"].get(
                "label"
            ), label.get("description")
            if description:
                opts_context["description"] = description

        return opts_context
