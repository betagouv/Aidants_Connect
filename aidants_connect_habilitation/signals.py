from django.dispatch import Signal

# Provides the arguments "request", "email_address"
email_confirmed = Signal()
# Provides the arguments "request", "confirmation", "signup"
email_confirmation_sent = Signal()
