import os
import requests as python_request
from django.shortcuts import render, redirect
from django.http import HttpResponse


fc_base = os.getenv('FRANCE_CONNECT_URL')
current_host = os.getenv('HOST')
fc_callback_uri = f'{current_host}/callback'

fc_client_id = os.getenv('FRANCE_CONNECT_CLIENT_ID')
fc_client_secret = os.getenv('FRANCE_CONNECT_CLIENT_SECRET')

def connection(request):
    return render(request, 'aidant_connect_web/connection.html')


def fc_authorize(request):

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

    authorize_url = f'{fc_base}/authorize?{parameters}'
    return redirect(authorize_url)


def fc_callback(request):

        code = request.GET.get("code")
        state = request.GET.get("state")

        token_url = f'{fc_base}/token'
        payload = {
            'grant_type': 'authorization_code',
            'redirect_uri': fc_callback_uri,
            'client_id': fc_client_id,
            'client_secret': fc_client_secret,
            'code': code
        }

        headers = {'Accept': 'application/json'}
        request_for_token = python_request.post(
            token_url,
            data=payload,
            headers=headers)
        content = request_for_token.json()

        fc_access_token = content.get('access_token')
        fc_id_token = content.get('id_token')

        headers_for_user_info = {'Authorization': f'Bearer {fc_access_token}'}
        request.session['user_info'] = python_request.get(
            f"{fc_base}/userinfo?schema=openid",
            headers=headers_for_user_info
            ).json()

        return redirect('/switchboard/')


def switchboard(request):
    user_info = request.session.get('user_info')
    return render(
        request,
        'aidant_connect_web/switchboard.html',
        {'user_info': user_info}
    )



