import uuid
import urlparse
import urllib

from flask import g, request

from mqetables import enrichment
from mqe import util
from mqe import reports
from mqe import serialize

from mqeapi import apiconfig
from mqeapi import responses


def set_query_param(url, param_name, param_value):
    pr = urlparse.urlparse(url)
    params_dict = urlparse.parse_qs(pr.query)
    params_dict[param_name] = param_value
    pr = pr._replace(query=urllib.urlencode(params_dict, True))
    return urlparse.urlunparse(pr)

def href(path):
    return apiconfig.BASE_URL_API + path

def to_id(uuid):
    return uuid.hex

def parse_id(s):
    if not s or not s.strip():
        return None
    try:
        return uuid.UUID(s)
    except ValueError:
        raise responses.ExceptionalResponse.bad_request('Invalid id format <%s>' % s)

def parse_datetime(s):
    if s is None or not s.strip():
        return None
    ev = enrichment.EnrichedValue(s)
    res = ev.optimistic_as_datetime
    if res is None:
        raise responses.ExceptionalResponse.bad_request('Invalid datetime <%s>' % s)
    return res

def parse_tags(s):
    if s is None:
        return None
    if s == '':
        return []
    tags = s.split(',')
    tags = [t for t in tags if t.strip()]
    return util.uniq_sameorder(tags)

def parse_int_tags(s):
    tags = parse_tags(s)
    if tags is None:
        return None

    res = []
    for x in tags:
        try:
            res.append(int(x))
        except ValueError:
            pass
    return res

def parse_bool(s):
    if not s:
        return None
    s = s.lower().strip()
    if s in {'', '0', 'false', 'f', 'no'}:
        return 0
    if s in {'1', 'true', 't', 'yes'}:
        return 1
    try:
        return int(s)
    except ValueError:
        raise responses.ExceptionalResponse.bad_request('Invalid bool/number format <%s>' % s)

def parse_int(s):
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        raise responses.ExceptionalResponse.bad_request('Invalid integer format <%s>' % s)

def parse_string(s, max_len=None):
    if not s or not s.strip():
        return None
    s = s.strip()
    if max_len is not None and len(s) > max_len:
        raise responses.ExceptionalResponse.bad_request('Value too long <%s>' % s)
    return s

def parse_enum(s, enum_values):
    val = parse_string(s)
    if not val:
        return None
    if val not in enum_values:
        raise responses.ExceptionalResponse.bad_request('Invalid value <%s>, must be one of: %s' % (
            val, ', '.join('<%s>' % ev for ev in enum_values)))
    return val

def parse_json(s):
    if not s or not s.strip():
        return None
    try:
        return serialize.json_loads(s)
    except:
        raise responses.ExceptionalResponse.bad_request('Invalid json value <%s>' % s)


def get_report(name):
    report = reports.Report.select_by_name(g.owner_id, name)
    if not report:
        raise responses.ExceptionalResponse(responses.ApiResponse(404, message='Report <%s> not found' % name))
    return report

def get_report_instance(report, report_instance_id):
    ri = report.fetch_single_instance(report_instance_id)
    if not ri:
        raise responses.ExceptionalResponse(responses.ApiResponse(404, message='Report instance with id <%s> not found' % to_id(report_instance_id)))
    return ri

def get_limit():
    limit = parse_int(request.args.get('limit'))
    if limit is None:
        limit = apiconfig.DEFAULT_GET_LIMIT

    if not 1 <= limit <= apiconfig.MAX_GET_LIMIT:
        raise responses.ExceptionalResponse(responses.ApiResponse(400, message='Invalid limit <%s>: must be between 1 and %s' % (limit, apiconfig.MAX_GET_LIMIT)))
    return limit

def client_ip():
    ff = request.headers.get('x-forwarded-for')
    if not ff:
        return request.remote_addr
    ff = ff.replace(' ', '')
    return ff.split(',', 1)[0]


