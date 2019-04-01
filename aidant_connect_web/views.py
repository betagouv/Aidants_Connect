import os
from django.shortcuts import render, redirect

# Create your views here.

def connection(request):
    return render(request, 'aidant_connect_web/connection.html')

def fc_authorize(request):
    base = os.getenv('FRANCE_CONNECT_URL')
    franceconnect_client_id = os.getenv('FRANCE_CONNECT_CLIENT_ID')
    current_host = os.getenv('HOST')
    franceconnect_callback_uri = f'{current_host}/callback'
    scopes = [
        "given_name",
        "family_name",
        "preferred_username",
        "birthdate",
        "gender",
        "birthplace",
        "birthcountry"
    ]
    franceconnect_scopes = 'openid' + ''.join(['%20' + scope for scope in scopes])
    franceconnect_state = 'customState11'
    franceconnect_nonce = 'customNonce11'

    parameters = f'response_type=code&client_id={franceconnect_client_id}&redirect_uri={franceconnect_callback_uri}&scope={franceconnect_scopes}&state={franceconnect_state}&nonce={franceconnect_nonce}'
    authorize_url = f'{base}/authorize?{parameters}'
    return redirect(authorize_url)

