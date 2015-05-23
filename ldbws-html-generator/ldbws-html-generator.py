from os import environ
from flask import Flask, jsonify, make_response, abort, Response, request
import csv
import logging
import string
import requests
from yattag import Doc
from dateutil.parser import parse
from pytz import timezone

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


def get_valid_crs_codes():
    with open('../res/station_codes.csv', 'rb') as station_codes:
        return [{'name': row['Station name'], 'code': row['Code']} for row in csv.DictReader(station_codes)]


valid_crs_codes = get_valid_crs_codes()
base_url = 'http://' + ldbws_rest_host + '/ldbws-rest-proxy/v0.1'
departure_board_url = base_url + '/departure-board'

css = "table{border-collapse:collapse;}\
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
body{font-family:Tahoma,Geneva,sans-serif;font-size:125%}\
"

def get_json(url):
    logging.debug('Querying REST service for path: ' + request.path)
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        abort(500)


def extract_locations(locations):
    return string.join([l.get('locationName') for l in locations], ', ')


def format_date(datetime):
    return parse(datetime).astimezone(timezone('Europe/London')).strftime('%Y-%m-%d %H:%M:%S %Z')


def generateHtml(j):
    doc, tag, text = Doc().tagtext()
    doc.asis('<!DOCTYPE html>')
    with tag('html'):
        with tag('head'):
            with tag('style'):
                doc.asis(css)
        with tag('body'):
            with tag('h1'):
                text('Live UK Train Departure Boards')
            with tag('h2'):
                text(j.get('locationName'))
                if 'filterLocationName' in j:
                    text(' to ' + j.get('filterLocationName'))

            text('Last Updated: ' + format_date(j.get('generatedAt')))
            with tag('table'):
                with tag('th'):
                    text('Operator')
                with tag('th'):
                    text('STD')
                with tag('th'):
                    text('ETD')
                with tag('th'):
                    text('Destination')
                with tag('th'):
                    text('Platform')

                if 'trainServices' not in j:
                    with tag('tr'):
                        with tag('td', colspan='5'):
                            text('No departures in the next 2 hours')
                else:
                    for s in j.get('trainServices'):
                        with tag('tr'):
                            with tag('td'):
                                text(s.get('operator'))
                            with tag('td'):
                                text(s.get('std'))
                            if s.get('etd') == 'On time':
                                with tag('td'):
                                    text(s.get('etd'))
                            else:
                                with tag('td', style='background-color:#ffcccc'):
                                    text(s.get('etd'))
                            with tag('td'):
                                text(extract_locations(s.get('destination')))
                            with tag('td'):
                                text(s.get('platform', '-'))

    return Response(doc.getvalue(), content_type='text/html')


@app.route('/', methods=['GET'])
def homepage():
    doc, tag, text = Doc().tagtext()
    doc.asis('<!DOCTYPE html>')
    with tag('html'):
        with tag('head'):
            with tag('style'):
                doc.asis(css)
        with tag('body'):
            with tag('h1'):
                text('Live UK Train Departure Boards')
            with tag('table'):
                with tag('th'):
                    text('Station')
                for station in valid_crs_codes:
                    with tag('tr'):
                        with tag('td'):
                            with tag('a', href='d/' + station['code']):
                                text(station['name'])
    return Response(doc.getvalue(), content_type='text/html')


@app.route('/d/<string:from_crs>', methods=['GET'])
def get_departure_board_from(from_crs):
    return generateHtml(get_json(departure_board_url + '/' + string.upper(from_crs)))


@app.route('/d/<string:from_crs>/<string:to_crs>', methods=['GET'])
def get_departure_board_from_to(from_crs, to_crs):
    return generateHtml(get_json(departure_board_url + '/' + string.upper(from_crs) + '/' + string.upper(to_crs)))


if __name__ == '__main__':
    app.run(debug=False, port=5002)