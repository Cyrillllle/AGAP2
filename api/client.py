import streamlit as st
import time
import pathlib
import shelve
import time
import hashlib
import requests
from dataclasses import dataclass
import json
import sqlite3
import urllib3




urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RequestType(enumerate) :
    GET_ALL_USERS = "GetAllUsers"
    SEARCH_USER   = "SearchUser"
    GET_USER_CV   = "GetUserCv"
    EXPORT_CV     = "ExportCv"

@dataclass
class GetAllUsers :
    apikey    : str
    timestamp : str
    filter    : str
    page      : int = 1
    limit     : int = 20

@dataclass
class SearchUser :
    apikey    : str
    timestamp : str
    term      : str
    limit     : int = 10

@dataclass
class GetUserCv :
    apikey    : str
    timestamp : str
    id        : str

@dataclass
class ExportCv :
    apikey     : str
    timestamp  : str
    id         : str
    # format     : str
    anonymized : str = "false"

@dataclass
class Response :
    status_code : int
    text        : str
    content     : object
    url         : str



BASE_URL = "https://showcase.doyoubuzz.com"

ENDPOINTS = {
    "GetAllUsers": {
        "path": "/api/v1/users",
        "path_params": []
    },
    "SearchUser": {
        "path": "/api/v1/users/search",
        "path_params": []
    },
    "GetUserCv": {
        "path": "/api/v1/users/{id}/cv",
        "path_params": ["id"]
    },
    "ExportCv": {
        "path": "/api/v1/cv/{id}/export/doc",
        "path_params": ["id"]
    }
}

if "page" not in st.session_state :
    st.session_state.page = "version"
if "first_test" not in st.session_state :
    st.session_state.first_test = True
if "token_state" not in st.session_state :
    st.session_state.token_state = 0

    
def construct_params_dict(obj) :
    return {
        key : value for key, value in vars(obj).items() if value is not None
    }

def construct_hash(params, secret) :
    sorted_keys = sorted(params.keys())
    concat_values = "".join(str(params[key]) for key in sorted_keys)
    string_to_hash = concat_values + secret
    
    hash_value = hashlib.md5(string_to_hash.encode())
    hash_value = hash_value.hexdigest()
    return hash_value

def build_url(request_type, params):
    endpoint = ENDPOINTS[request_type]
    
    for p in endpoint["path_params"]:
        if p not in params:
            raise ValueError(f"Paramètre requis manquant : {p}")

    path = endpoint["path"].format(**params)

    return BASE_URL + path

def split_params(params, path_params):
    query_params = params.copy()
    for p in path_params:
        query_params.pop(p, None)
    return query_params

def api_request(secret, request_type : RequestType, params) :
    endpoint = ENDPOINTS[request_type]
    dict_params = construct_params_dict(params)
    query_params = dict_params

    query_params["timestamp"] = str(int(time.time()))
    query_params["hash"] = construct_hash(query_params, secret)

    url = build_url(request_type, query_params)
    # query_params = split_params(dict_params, endpoint["path_params"])

    response = requests.get(url, params=query_params, verify=False)
    
    return Response(response.status_code, response.text, response.content, response.url)