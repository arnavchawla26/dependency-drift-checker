import os
import json
import requests
import yaml
from . import helpers
from .helpers import greet
import jinja2


def run():
    return requests.get, yaml.safe_load, json.dumps, os.getcwd, helpers, greet, jinja2
