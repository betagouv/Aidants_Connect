import os
from django.shortcuts import render, redirect


def connection(request):
    return render(request, 'aidant_connect_web/connection.html')


def fc_authorize(request):
    base = os.getenv('FRANCE_CONNECT_URL')
    current_host = os.getenv('HOST')
    fc_client_id = os.getenv('FRANCE_CONNECT_CLIENT_ID')
    fc_callback_uri = f'{current_host}/callback'
    fc_scopes = [
        'given_name',
        'family_name',
        'preferred_username',
        'birthdate',
        'gender',
        'birthplace',
        'birthcountry'
    ]

    fc_state = 'customState11'
    fc_nonce = 'customNonce11'

    parameters = \
        f"response_type=code" \
        f"&client_id={fc_client_id}" \
        f"&redirect_uri={fc_callback_uri}" \
        f"&scope={'openid' + ''.join(['%20' + scope for scope in fc_scopes])}" \
        f"&state={fc_state}" \
        f"&nonce={fc_nonce}"

    authorize_url = f'{base}/authorize?{parameters}'
    return redirect(authorize_url)
