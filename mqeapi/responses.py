import logging
from collections import OrderedDict
import json

from flask import request

from werkzeug.wrappers import Response
from werkzeug import http

from mqe import serialize


log = logging.getLogger('mqeapi.responses')


def fallback_response():
    d = OrderedDict()
    d['success'] = False
    d['details'] = OrderedDict()
    d['details']['message'] = 'Internal error'
    d['details']['errorCode'] = 'ERROR_500'
    data = json.dumps(d, indent=2)
    return Response(data, status=500, mimetype='application/json')


class ApiResponse(object):

    def __init__(self, status=None, success=None, details=None, result=None, result_pairs=None, message=None, docs=None, error_code=None, details_pairs=None):
        self.status = status
        self.success = success
        self.details = details
        if details_pairs:
            for k, v in details_pairs:
                self.set_detail(k, v)
        self.result = result
        if message is not None:
            self.message = message
        if docs is not None:
            self.docs = docs
        if error_code is not None:
            self.error_code = error_code
        if result_pairs is not None:
            self.result_pairs = result_pairs

    def set_detail(self, k, v):
        if self.details is None:
            self.details = OrderedDict()
        self.details[k] = v

    @property
    def error_code(self):
        return self.details['errorCode']
    @error_code.setter
    def error_code(self, v):
        self.set_detail('errorCode', v)

    @property
    def message(self):
        return self.details['message']
    @message.setter
    def message(self, msg):
        self.set_detail('message', msg)

    @property
    def result_pairs(self):
        if isinstance(self.result, dict):
            return self.result.items()
        return None
    @result_pairs.setter
    def result_pairs(self, pairs):
        self.result = OrderedDict(pairs)

    def get(self):
        try:
            return self._do_get()
        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            log.exception('Encoding error when serializing json response, returning fallback response')
            return bad_request('Can\'t encode response to UTF-8').get()
        except:
            log.exception('Error when serializing json response')
            return fallback_response()

    def _sorted_details(self):
        def sort_key((pos, k)):
            if k == 'errorCode':
                return (1, 0)
            if k == 'message':
                return (0, 0)
            return (2, pos)
        pos_keys = sorted(enumerate(self.details.keys()), key=sort_key)
        return OrderedDict([(pk[1], self.details[pk[1]]) for pk in pos_keys])

    def _do_get(self):
        assert self.status in http.HTTP_STATUS_CODES

        if self.success is None:
            self.success = self.status == 200
        if not self.success and (self.details is None or self.details.get('errorCode') is None):
            self.error_code = 'ERROR_%s' % (self.status if self.status != 200 else 'OTHER')

        d = OrderedDict()
        d['success'] = self.success
        if self.details is not None:
            d['details'] = self._sorted_details()
        if self.result is not None:
            d['result'] = self.result
        data = serialize.json_dumps_external(d)
        return Response(data, status=self.status, mimetype='application/json')


def not_found():
    resp = ApiResponse(404, False)
    resp.message = """Resource '%s' not found""" % (request.path)
    resp.error_code = 'ERROR_404'
    return resp

def unauthorized():
    resp = ApiResponse(401, False)
    resp.message = """Unable to find a valid API key. Use Basic Authentication with an API key as a username, or use GET parameter <key>"""
    resp.error_code = 'ERROR_401'
    return resp

def bad_request(message):
    return ApiResponse(400, message=message)

def method_not_allowed():
    resp = ApiResponse(405, False)
    resp.message = """The method %s is not allowed for the resource '%s'""" % \
                   (request.method, request.path)
    resp.error_code = 'ERROR_405'
    return resp


class ExceptionalResponse(Exception):

    def __init__(self, response):
        super(ExceptionalResponse, self).__init__(str(response.status))
        self.response = response

    @staticmethod
    def bad_request(message):
        return ExceptionalResponse(ApiResponse(400, message=message))

