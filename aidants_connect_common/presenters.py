"""
Presenters are classes that present data to HTML templates from different data sources
"""

from abc import ABC, abstractmethod
from typing import Any

from django.db.models import Model


class GenericHabilitationRequestPresenter(ABC):
    """Presenter to use with habilitation/generic-habilitation-request-profile-card.html"""  # noqa: E501

    @property
    @abstractmethod
    def pk(self) -> Model:
        """Return the underlying object containing data"""
        ...

    @property
    def details_id(self) -> str | None:
        """<details>' `id` parameter"""
        return None

    @property
    @abstractmethod
    def edit_endpoint(self) -> str | None:
        pass

    @property
    @abstractmethod
    def full_name(self) -> str:
        pass

    @property
    @abstractmethod
    def email(self) -> str:
        pass

    @property
    @abstractmethod
    def details_fields(self) -> list[dict[str, Any]]:
        pass

    @property
    def form(self) -> str:
        """
        Use this to render a hidden for containing this object's data, if needed.
        Use this with formsets.
        """
        return ""

    @property
    def summary_second_line_tpl(self):
        return "habilitation/generic-habilitation-request-profile-card.html#summary-second-line"  # noqa: E501
