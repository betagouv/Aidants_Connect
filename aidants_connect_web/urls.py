from django.conf import settings
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView

from magicauth import settings as magicauth_settings
from magicauth.urls import urlpatterns as magicauth_urls

from aidants_connect_web.api.urls import router as api_router
from aidants_connect_web.legacy_url_redirects import (
    LEGACY_ESPACE_RESPONSABLE_URLPATTERNS,
    LEGACY_ROOT_AIDANT_URLPATTERNS,
)
from aidants_connect_web.views import (
    FC_as_FS,
    formations,
    id_provider,
    login,
    others,
    sandbox,
    service,
    sms,
)

urlpatterns = [
    # connexion choice
    path(
        f"{settings.URL_CONNEXIONCHOICE}/ad_connexion_choice",
        others.ConnexionChoiceView.as_view(),
        name="connexion_choice",
    ),
    # mobile asking
    path(
        f"{settings.URL_ASK_MOBILE}/<str:referent_id>/mobile_asking_referent/",
        others.AskingMobileView.as_view(),
        name="asking_mobile",
    ),
    path(
        "thanks_asking_mobile/",
        others.ThanksAskingMobileView.as_view(),
        name="thanks_asking_mobile",
    ),
    # service
    path("accounts/login/", login.LoginView.as_view(), name="login"),
    path(
        "accounts/manager_first_login/",
        login.ManagerFirstLoginView.as_view(),
        name="manager_first_login",
    ),
    path(
        "accounts/manager_first_connexion_email_sent/",
        login.ManagerFirstLoginEmailSentView.as_view(),
        name="manager_first_connexion_email_sent",
    ),
    path(
        f"accounts/manager_first_login_with_code/{settings.URL_FIRST_LOGIN_REFERENT}/<str:manager_id>/",  # noqa
        login.ManagerFirstLoginWithCodeView.as_view(),
        name="manager_first_login_with_code",
    ),
    path(magicauth_settings.LOGIN_URL, login.LoginRedirect.as_view()),
    path("logout-session/", service.logout_page, name="logout"),
    path("activity_check/", service.activity_check, name="activity_check"),
    # Legacy aidant URLs (root-level) → /espace-aidant/... (see legacy_url_redirects)
    *LEGACY_ROOT_AIDANT_URLPATTERNS,
    path(
        "espace-aidant/",
        include("aidants_connect_web.urls_espace_aidant"),
    ),
    # Legacy espace responsable → espace référent (explicit patterns)
    *LEGACY_ESPACE_RESPONSABLE_URLPATTERNS,
    path(
        "espace-referent/",
        include("aidants_connect_web.urls_espace_referent"),
    ),
    # id_provider
    path("authorize/", id_provider.Authorize.as_view(), name="authorize"),
    path("token/", id_provider.Token.as_view(), name="token"),
    path("userinfo/", id_provider.user_info, name="user_info"),
    path(
        "select_demarche/",
        id_provider.FISelectDemarche.as_view(),
        name="fi_select_demarche",
    ),
    path(
        "logout/",
        id_provider.end_session_endpoint,
        name="end_session_endpoint",
    ),
    # FC_as_FS
    path("fc_authorize/", FC_as_FS.FCAuthorize.as_view(), name="fc_authorize"),
    path("fc_authorizev2/", FC_as_FS.FCAuthorize.as_view(), name="fc_authorizev2"),
    path("callback/", FC_as_FS.fc_callback, name="fc_callback"),
    path("callbackv2/", FC_as_FS.fc_callback_v2, name="fc_callbackv2"),
    # public_website
    path("", service.home_page, name="home_page"),
    path("stats/", service.StatistiquesView.as_view(), name="statistiques"),
    path("cgu/", service.cgu, name="cgu"),
    path(
        "politique_confidentialite/",
        service.politique_confidentialite,
        name="politique_confidentialite",
    ),
    path("mentions-legales/", service.mentions_legales, name="mentions_legales"),
    path("budget/", service.budget, name="budget"),
    path(
        "guide_utilisation/",
        RedirectView.as_view(
            url="https://docs.numerique.gouv.fr/docs/6d7aa937-9030-4af4-9522-3a725ceda6da/",  # noqa: E501
            permanent=True,
        ),
        name="guide_utilisation",
    ),
    path("formation/", service.formation, name="habilitation_faq_formation"),
    path("habilitation/", service.habilitation, name="habilitation_faq_habilitation"),
    path("ressources/", service.ressources, name="ressources"),
    path("accessibilite/", service.AccessibiliteView.as_view(), name="accessibilite"),
    # # SMS
    # SMS provider may misconfigure the trailing slash so we need to respond on both
    re_path(r"sms/callback/?$", sms.Callback.as_view(), name="sms_callback"),
    # # Bac à sable
    path(
        "bac-a-sable/presentation",
        sandbox.Sandbox.as_view(),
        name="sandbox_presentation",
    ),
    path("api/", include(api_router.urls)),
    path(
        f"formations/{settings.URL_FORMATION}/listing",
        formations.FormationsListing.as_view(),
        name="listing_formations",
    ),
    path("plan-du-site/", service.SitemapView.as_view(), name="sitemap"),
]

urlpatterns.extend(magicauth_urls)
