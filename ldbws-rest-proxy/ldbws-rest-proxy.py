# Proxy server to hide the horribleness of SOAP from clients.
# Presents a REST interface to clients

# Currently only implements GetDepartureBoard() as a proof of concept.

from suds.client import Client
from suds.sax.element import Element
from os.path import expanduser, join
from flask import Flask, jsonify, make_response, abort
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logging.getLogger('suds.client').setLevel(logging.DEBUG)

access_token_path = join(expanduser("~"), '.ldbws-access-token')


def contents_of(path):
    with open(path, 'r') as f:
        return f.read().strip()

access_token = contents_of(access_token_path)


@app.errorhandler(500)
def not_found(error):
    return make_response(jsonify({'error': 'Internal error'}), 500)


def extract_fields(source, primitive_fields=[], object_fields=[]):
    r = {}

    for field in primitive_fields:
        if field in source and source[field] is not None:
            r[field] = source[field]

    for o in object_fields:
        parser = o['parser']
        for field in o['fields']:
            if field in source:
                r[field] = parser(source[field])
    return r


def parse_service_location(x):
    return extract_fields(x, ['futureChangeTo', 'via', 'crs', 'locationName', 'assoclsCancelled'])


def parse_array_of_service_location(x):
    return [parse_service_location(i) for i in x.location]


def parse_array_of_adhoc_alerts(x):
    return [i for i in x.adhocAlertText]


def parse_service_item(x):
    return extract_fields(
        x,
        ['sta', 'eta', 'std', 'etd', 'platform', 'operator', 'operatorCode', 'isCircularRoute', 'serviceID'],
        [{'parser': parse_array_of_service_location, 'fields': ['origin', 'destination']},
         {'parser': parse_array_of_adhoc_alerts, 'fields': ['adhocAlerts']}])


def parse_array_of_service_item(x):
    return [parse_service_item(i) for i in x.service]


def parse_array_of_nrcc_messages(x):
    return [i for i in x.message]


def parse_station_board(x):
    return extract_fields(
        x,
        ['generatedAt', 'locationName', 'crs', 'filterLocationName', 'filtercrs',
         'filterType', 'platformAvailable', 'areServicesAvailable'],
        [{'parser': parse_array_of_service_item, 'fields': ['trainServices', 'busServices', 'ferryServices']},
         {'parser': parse_array_of_nrcc_messages, 'fields': ['nrccMessages']}])


def parse_calling_points(x):
    return extract_fields(
        x,
        ['locationName', 'crs', 'st', 'et', 'at'],
        [{'parser': parse_array_of_adhoc_alerts, 'fields': ['adhocAlerts']}])


def parse_array_of_calling_points(x):
    return [parse_calling_points(i) for i in x.callingPoint]


def parse_array_of_array_of_calling_points(x):
    return [parse_array_of_calling_points(i) for i in x.callingPointList]


def parse_service_details(x):
    return extract_fields(
        x,
        ['generatedAt', 'serviceType', 'locationName', 'crs', 'operator', 'operatorCode', 'isCancelled',
         'disruptionReason', 'overdueMessage', 'platform', 'sta', 'eta', 'ata', 'std', 'etd', 'atd'],
        [{'parser': parse_array_of_adhoc_alerts, 'fields': ['adhocAlerts']},
         {'parser': parse_array_of_array_of_calling_points, 'fields': ['previousCallingPoints', 'subsequentCallingPoints']}])

def get_service():
    client = Client('https://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx?ver=2014-02-20')

    ns_common_types = ('com', 'http://thalesgroup.com/RTTI/2010-11-01/ldb/commontypes')
    el_token_value = Element('TokenValue', ns=ns_common_types)
    el_token_value.setText(access_token)

    el_access_token = Element('AccessToken', ns=ns_common_types).insert(el_token_value)
    client.set_options(soapheaders=el_access_token)

    return client.service


@app.route('/ldbws-rest-proxy/v0.1/departure-board/<string:from_crs>', methods=['GET'])
def get_departure_board_from(from_crs):
    try:
        soap_response = get_service().GetDepartureBoard(numRows=50, crs=from_crs)
        resp = parse_station_board(soap_response)
        return jsonify(resp)
    except Exception as e:
        logging.error(e.message)
        abort(500)


@app.route('/ldbws-rest-proxy/v0.1/departure-board/<string:from_crs>/<string:to_crs>', methods=['GET'])
def get_departure_board_from_to(from_crs, to_crs):
    try:
        soap_response = get_service().GetDepartureBoard(numRows=50, crs=from_crs, filterCrs=to_crs, filterType='to')
        resp = parse_station_board(soap_response)
        return jsonify(resp)
    except Exception as e:
        logging.error(e.message)
        abort(500)


@app.route('/ldbws-rest-proxy/v0.1/service-details/<string:service_id>', methods=['GET'])
def get_service_details(service_id):
    try:
        soap_response = get_service().GetServiceDetails(serviceID=service_id)
        resp = parse_service_details(soap_response)
        return jsonify(resp)
    except Exception as e:
        logging.error(e.message)
        abort(500)

if __name__ == '__main__':
    app.run(debug=True)
