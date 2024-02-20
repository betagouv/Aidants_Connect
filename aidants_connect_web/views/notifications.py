import contextlib

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, ListView

from aidants_connect_web.constants import NotificationType
from aidants_connect_web.decorators import aidant_logged_with_activity_required
from aidants_connect_web.models import Notification


@aidant_logged_with_activity_required
class Notifications(ListView):
    template_name = "aidants_connect_web/notifications/notification_list.html"
    paginate_by = 100
    context_object_name = "notifications"

    def dispatch(self, request, *args, **kwargs):
        self.type_filter = None
        with contextlib.suppress(ValueError):
            self.type_filter = NotificationType(request.GET.get("type"))

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        filter_kwargs = {"aidant": self.request.user}
        if self.type_filter:
            filter_kwargs["type"] = self.type_filter
        return Notification.objects.filter(**filter_kwargs).order_by("-date").all()


@aidant_logged_with_activity_required
class NotificationDetail(DetailView):
    template_name = "aidants_connect_web/notifications/notification_detail.html"
    context_object_name = "notification"

    def get_object(self, queryset=None):
        return get_object_or_404(
            Notification,
            aidant=self.request.user,
            pk=self.kwargs.get("notification_id"),
        )


@method_decorator([csrf_exempt, login_required], name="dispatch")
class MarkNotification(View):
    def dispatch(self, request, *args, **kwargs):
        self.notification = get_object_or_404(
            Notification, pk=kwargs.get("notification_id"), aidant=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.notification.mark_unread()
        return HttpResponse(status=200)

    def delete(self, request, *args, **kwargs):
        self.notification.mark_read()
        return HttpResponse(status=200)
