class SpecificDeleteActionsMixin:
    def get_actions(self, request):
        actions = super().get_actions(request)
        try:
            del actions["delete_selected"]
        except KeyError:
            pass
        return actions

    def _specific_delete_action(self, request, queryset):
        for one_object in queryset:
            if one_object.clean_journal_entries_and_delete_mandats(request):
                one_object.delete()
