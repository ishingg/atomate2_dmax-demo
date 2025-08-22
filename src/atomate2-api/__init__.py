"""Atomate2 is a library of computational materials science workflows."""

#from _version import __version__
#from settings import Atomate2Settings
from flask import Flask, request
from flask_restful import Api


app = Flask(__name__)
api = Api(app)
#SETTINGS = Atomate2Settings()

import routes 