from os import environ
from flask import Flask, jsonify, make_response, abort, Response, request
import logging
import string
import requests

app = Flask(__name__)

logging.basicConfig(filename='ldbws-html-generator.log', level=logging.INFO)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.errorhandler(500)
def internal_error(error):
    return make_response(jsonify({'error': 'Internal Error'}), 500)


# IP address or hostname of a REST proxy service must be in the environment variable LDBWS_HOST.
#
# Because the ldbws-rest-proxy and ldbws-redis-cache services expose the same interface, this
# works with either (obviously use ldbws-redis-cache to get free caching)
ldbws_rest_host = environ.get('LDBWS_REST_HOST')
if ldbws_rest_host is None:
    logging.fatal("Environment variable LDBWS_REST_HOST not set")
    exit(1)

base_url = 'http://' + ldbws_rest_host + '/ldbws-rest-proxy/v0.1'
departure_board_url = base_url + '/departure-board'
css = "<style>\
table{border-collapse:collapse;}\
td,th{padding:0.5em;}\
table,th,td{\
width:100%;\
background:#ffffff;\
margin:2em 0em;\
border:2px solid #d0d0d0;\
box-shadow:none;\
color:rgba(0,0,0,0.8);\
border-spacing:5px;\
width:auto;\
}\
</style>"

def get_json(url):
    logging.debug('Querying REST service for path: ' + request.path)
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        abort(500)


def extract_locations(locations):
    return string.join([l.get('locationName') for l in locations], ', ')


def generateHtml(j):
    h = '<html><head>' + css + '</head><h1>Live UK Train Departure Boards</h1>' + \
        '<h2>' + j.get('locationName')

    if 'filterLocationName' in j:
        h += ' to ' + j.get('filterLocationName')

    h += '</h2>' + \
        'Last Updated: ' + j.get('generatedAt') + \
        '<table><tr><th>Operator</th><th>STD</th><th>ETD</th><th>Destination</th><th>Platform</th></tr>'

    for s in j.get('trainServices'):
        h += '<tr><td>' + s.get('operator') + '</td><td>' + s.get('std') + '</td><td>' + s.get('etd') + \
            '</td><td>' + extract_locations(s.get('destination')) + '</td><td>' + s.get('platform', '-') + '</td></tr>'

    h += '</table></html>'

    return Response(h, content_type='text/html')


@app.route('/d/<string:from_crs>', methods=['GET'])
def get_departure_board_from(from_crs):
    return generateHtml(get_json(departure_board_url + '/' + string.upper(from_crs)))


@app.route('/d/<string:from_crs>/<string:to_crs>', methods=['GET'])
def get_departure_board_from_to(from_crs, to_crs):
    return generateHtml(get_json(departure_board_url + '/' + string.upper(from_crs) + '/' + string.upper(to_crs)))


if __name__ == '__main__':
    app.run(debug=False, port=5002)