from django.http import Http404, HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import RedirectView, View
from django.views.generic.detail import DetailView

from aidants_connect_common.utils import render_markdown
from aidants_connect_pico_cms import constants
from aidants_connect_pico_cms.models import FaqCategory, Testimony
from aidants_connect_web.models import Aidant


class TestimoniesView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        testimony_qs = Testimony.objects.for_display()
        if not testimony_qs.exists():
            return reverse("espace_aidant_home")

        return reverse("temoignages_detail", kwargs={"slug": testimony_qs.first().slug})


class TestimonyView(DetailView):
    model = Testimony

    def get_context_data(self, **kwargs):
        kwargs.update({"all_testimonies": Testimony.objects.for_display()})
        return super().get_context_data(**kwargs)


class FaqCategoryView(DetailView):
    template_name = "aidants_connect_pico_cms/faqcategory_detail.html"
    model = FaqCategory
    theme_filter = None

    def dispatch(self, request, *args, **kwargs):
        self.see_draft = "see_draft" in getattr(
            self.request, self.request.method.upper(), {}
        )
        return super().dispatch(request, *args, **kwargs)

    @property
    def should_show_drafts(self):
        return (
            isinstance(self.request.user, Aidant)
            and self.request.user.is_staff
            and self.see_draft
        )

    def get_extra_kwargs_filter(self):
        if self.theme_filter:
            return {"theme": self.theme_filter}
        return {}

    def get_queryset(self):
        cat_kwargs = {} if self.should_show_drafts else {"published": True}
        cat_kwargs.update(self.get_extra_kwargs_filter())
        return super().get_queryset().filter(**cat_kwargs).order_by("sort_order")

    def get_context_data(self, **kwargs):
        if not self.object:
            self.object: FaqCategory = self.get_object()

        kwargs.update(
            {
                "categories": self.get_queryset(),
                "questions": self.object.get_questions(self.should_show_drafts),
            }
        )
        return super().get_context_data(**kwargs)


class MixinFaqDefault:
    def get_object(self, queryset=None):
        first_published_category = self.get_queryset().first()

        if not first_published_category:
            raise Http404

        return first_published_category


class FaqDefaultView(MixinFaqDefault, FaqCategoryView):
    pass


@method_decorator(csrf_exempt, name="dispatch")
class MarkdownRenderView(View):
    def post(self, request, *args, **kwargs):
        return HttpResponse(render_markdown(self.request.POST.get("body", "")))


class PublicFaqCategoryView(FaqCategoryView):
    theme_filter = constants.FAQ_THEME_PUBLIC


class PublicFaqDefaultView(MixinFaqDefault, PublicFaqCategoryView):
    pass


class AidantFaqCategoryView(FaqCategoryView):
    theme_filter = constants.FAQ_THEME_AIDANT


class AidantFaqDefaultView(MixinFaqDefault, AidantFaqCategoryView):
    pass


class ReferentFaqCategoryView(FaqCategoryView):
    theme_filter = constants.FAQ_THEME_REFERENT


class ReferentFaqDefaultView(MixinFaqDefault, ReferentFaqCategoryView):
    pass
