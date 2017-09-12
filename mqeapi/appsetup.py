import logging
import time

from flask import request_started, request_finished, request, abort, g

from mqe import c

from mqeapi import responses


log = logging.getLogger('mqeapi')


@request_started.connect_via(c.app)
def log_request_start(*args, **kwargs):
    g.request_start_time = time.time()
    log.info('HTTP_START %s %s', request.method, request.url)

@request_finished.connect_via(c.app)
def log_request_end(*args, **kwargs):
    log.info('HTTP_END %s %s %s (%.1f)', request.method, request.url,
             kwargs['response'].status_code, (time.time() - g.request_start_time) * 1000)

@request_started.connect_via(c.app)
def authenticate_owner(*args, **kwargs):
    def possible_api_keys():
        if request.authorization:
            yield request.authorization.get('username')
            yield request.authorization.get('password')
        yield request.args.get('key')

    for api_key in possible_api_keys():
        if not api_key:
            continue
        owner_id = c.dao.ApiKeyDAO.select_user_id(api_key)
        if owner_id is not None:
            g.owner_id = owner_id
            g.api_key = api_key
            return
    abort(401)


@c.app.errorhandler(400)
def error_400(e):
    return responses.bad_request('Bad request').get()

@c.app.errorhandler(401)
def error_401(e):
    return responses.unauthorized().get()

@c.app.errorhandler(404)
def error_404(e):
    return responses.not_found().get()

@c.app.errorhandler(405)
def error_404(e):
    return responses.method_not_allowed().get()

@c.app.errorhandler(500)
def error_500(e):
    log.exception('Request exception')
    return responses.fallback_response()

@c.app.errorhandler(responses.ExceptionalResponse)
def handle_exceptional_response(e):
    return e.response.get()

