from os import environ
from flask import Flask, jsonify, make_response, abort, Response, request
import csv
import logging
import requests

import redis

app = Flask(__name__)

logging.basicConfig(filename='ldbws-redis-cache.log', level=logging.INFO)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.errorhandler(500)
def internal_error(error):
    return make_response(jsonify({'error': 'Internal Error'}), 500)


# IP address or hostname of the rest proxy service must be in the environment variable LDBWS_PROXY_HOST
ldbws_proxy_host = environ.get('LDBWS_REST_PROXY')
if ldbws_proxy_host is None:
    logging.fatal("Environment variable LDBWS_REST_PROXY not set")
    exit(1)


redis_host = environ.get('REDIS_HOST')
if redis_host is None:
    logging.fatal("Environment variable REDIS_HOST not set")
    exit(1)


def get_valid_crs_codes():
    with open('station_codes.csv', 'rb') as station_codes:
        return [row['Code'] for row in csv.DictReader(station_codes)]


valid_crs_codes = set(get_valid_crs_codes())


r = redis.StrictRedis(host=redis_host, db=0)


def get_cached(request):
    try:
        logging.debug('Checking cache for path: ' + request.path)
        cached_response = r.get(request.path)
        if cached_response is not None:
            logging.debug('Returning cached result for path: ' + request.path)
            return Response(cached_response, mimetype='text/json')
        else:
            logging.debug('Querying proxy for path: ' + request.path)
            url = 'http://' + ldbws_proxy_host + request.path
            response = requests.get(url)
            if response.status_code == 200:
                logging.debug('Caching result for path: ' + request.path)
                j = response.content
                r.setex(name=request.path, value=j, time=300)  # expire in 5 minutes (300 seconds)
                return Response(j, mimetype='text/json')

        abort(500)
    except Exception as e:
        logging.error(e.message)
        abort(500)


@app.route('/ldbws-rest-proxy/v0.1/departure-board/<string:from_crs>', methods=['GET'])
def get_departure_board_from(from_crs):
    if from_crs not in valid_crs_codes:
        abort(404)

    return get_cached(request)


@app.route('/ldbws-rest-proxy/v0.1/departure-board/<string:from_crs>/<string:to_crs>', methods=['GET'])
def get_departure_board_from_to(from_crs, to_crs):
    if from_crs not in valid_crs_codes or to_crs not in valid_crs_codes:
        abort(404)

    return get_cached(request)


@app.route('/ldbws-rest-proxy/v0.1/arrival-board/<string:to_crs>', methods=['GET'])
def get_arrival_board_to(to_crs):
    if to_crs not in valid_crs_codes:
        abort(404)

    return get_cached(request)


@app.route('/ldbws-rest-proxy/v0.1/arrival-board/<string:to_crs>/<string:from_crs>', methods=['GET'])
def get_arrival_board_to_from(to_crs, from_crs):
    if to_crs not in valid_crs_codes or from_crs not in valid_crs_codes:
        abort(404)

    return get_cached(request)


@app.route('/ldbws-rest-proxy/v0.1/service-details/<path:service_id>', methods=['GET'])
def get_service_details(service_id):
    return get_cached(request)


if __name__ == '__main__':
    app.run(debug=False, port=5001)
