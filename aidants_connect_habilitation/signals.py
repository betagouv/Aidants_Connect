from django.dispatch import Signal

"""
Both signals provide the arguments `request`: django.http.HttpRequest
and `confirmation`: aidants_connect_habilitation.models.IssuerEmailConfirmation
"""


email_confirmed = Signal()
email_confirmation_sent = Signal()
