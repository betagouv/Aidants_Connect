from .service import (
    home_page,
    logout_page,
    mandats,
    new_mandat,
    recap,
    authorize,
    token,
    user_info,
    humanize_demarche_names,
    fi_select_demarche,
    generate_mandat_pdf,
)
from .FC_as_FS import fc_authorize, fc_callback

__all__ = [
    home_page,
    logout_page,
    mandats,
    new_mandat,
    recap,
    authorize,
    token,
    user_info,
    humanize_demarche_names,
    fc_authorize,
    fc_callback,
    fi_select_demarche,
    generate_mandat_pdf,
]
