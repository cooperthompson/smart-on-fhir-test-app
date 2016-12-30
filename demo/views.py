from django.shortcuts import render
import fhirclient.models.conformance as fhir_conformance
import requests
import urllib
import json
import base64

# Create your views here.
from django.urls import reverse

def index(request):
    if request.GET.get('code') != "":
        return auth(request)

    context = {
        'query_params': request.GET
    }
    return render(request, 'index.html', context)


def launch(request):
    iss = request.GET.get('iss')
    launch_code = request.GET.get('launch')

    client_id = '076376f4-a432-472f-9ea6-db57b16f3b62'
    zephyr_url = 'http://zephyr/Dev/ClientGarden/Edit/440'
    conformance_url = 'https://vs-icx.epic.com/Interconnect-CDE/api/FHIR/DSTU2/metadata'  # TODO build from iss

    # Query Conformance
    (authorize_url, token_url) = parse_conformance(conformance_url)

    # Exchange launch token for auth code
    params = {'response_type': 'code',
              'client_id': client_id,
              'redirect_uri': request.build_absolute_uri(reverse('index')),
              'state': conformance_url
              }
    # manually build query params to avoid URL encoding the *launch key
    params_encoded = urllib.urlencode(params) + "&" + "scope=+launch:" + urllib.quote(launch_code)

    authorize_request = requests.get(authorize_url, params=params_encoded, verify=False)
    authorize_response = authorize_request.text

    debug_info = {
        'launch_code': launch_code,
        'client_id': client_id,
        'zephyr_url': zephyr_url,
        'conformance_url': conformance_url,
        'redirect_uri': request.build_absolute_uri(reverse('index')),
        'authorize_url': authorize_url,
        'token_url': token_url
    }

    requests_info = {
        'history': authorize_request.history,
        'request': authorize_request,
    }

    url = request.build_absolute_uri(request.get_full_path())
    context = {
        'debug_info': debug_info,
        'requests_info': requests_info,
        'query_params': request.GET,
        'url': url,
        'authorize_response': authorize_response
    }
    return render(request, 'launch.html', context)


def auth(request):
    auth_code = request.GET.get('code')
    state = request.GET.get('state')

    # TODO: move to session
    client_id = '076376f4-a432-472f-9ea6-db57b16f3b62'
    zephyr_url = 'http://zephyr/Dev/ClientGarden/Edit/440'

    conformance_url = state
    (authorize_url, token_url) = parse_conformance(conformance_url)

    # Exchange auth code for launch code
    params = {'grant_type': 'authorization_code',
              'client_id': client_id,
              'code': auth_code,
              'redirect_uri': request.build_absolute_uri(reverse('index')),
              }
    token_request = requests.post(token_url, data=params, verify=False)
    token_response = token_request.text

    response = json.loads(token_request.text)
    patient = response.get('patient')
    access_token = response.get('access_token')

    debug_info = {
        'client_id': client_id,
        'zephyr_url': zephyr_url,
        'conformance_url': conformance_url,
        'redirect_uri': request.build_absolute_uri(reverse('index')),
        'authorize_url': authorize_url,
        'token_url': token_url,
    }
    debug_info.update(response)

    requests_info = {
        'history': token_request.history,
        'request': token_request,
    }

    patient_fhir_read_url = conformance_url.replace('metadata','patient') + "/" + patient
    headers = {'Epic-Client-ID': client_id, 'Accept': 'application/json'}
    patient_fhir_content = requests.get(patient_fhir_read_url, headers=headers, verify=False)
    url = request.build_absolute_uri(request.get_full_path())
    context = {
        'debug_info': debug_info,
        'requests_info': requests_info,
        'query_params': request.GET,
        'url': url,
        'authorize_response': token_response,
        'patient': json.dumps(patient_fhir_content.text, indent=4)
    }
    return render(request, 'auth.html', context)


def parse_conformance(conformance_url):
    client_id = '076376f4-a432-472f-9ea6-db57b16f3b62'
    headers = {'Epic-Client-ID': client_id, 'Accept': 'application/json'}
    conformance_request = requests.get(conformance_url, headers=headers, verify=False)
    conformance = fhir_conformance.Conformance(json.loads(conformance_request.text))

    # Parse Conformance
    for rest in conformance.rest:
        for extension in rest.security.extension:
            if extension.url != 'http://fhir-registry.smarthealthit.org/StructureDefinition/oauth-uris':
                continue
            for url_extension in extension.extension:
                if url_extension.url == 'authorize':
                    authorize_url = url_extension.valueUri
                if url_extension.url == 'token':
                    token_url = url_extension.valueUri

    return (authorize_url, token_url)