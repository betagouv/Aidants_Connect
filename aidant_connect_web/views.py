from django.shortcuts import render

# Create your views here.

def connection(request):

    return render(request, 'aidant_connect_web/connection.html')
