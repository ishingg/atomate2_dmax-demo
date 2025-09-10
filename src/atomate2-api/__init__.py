"""Atomate2 is a library of computational materials science workflows."""

#from _version import __version__
#from settings import Atomate2Settings
from flask import Flask, request
from flask_restful import Api


app = Flask(__name__)
api = Api(app)


# For CORS
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE")
    return response
    
#SETTINGS = Atomate2Settings()

import routes 