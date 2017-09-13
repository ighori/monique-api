from collections import OrderedDict
import logging

from flask import Blueprint, request, g

from mqetables import parseany
from mqe import reports
from mqe.util import uuid_for_prev_dt, uuid_for_next_dt
from mqe import mqeconfig

from mqeapi.responses import ApiResponse, bad_request
from mqeapi.apiutil import *
from mqeapi import apiconfig


log = logging.getLogger('mqeapi.views')


bp_api = Blueprint('bp_api', 'mqeapi.views')


@bp_api.route('/reports', methods=['GET'])
def get_reports():
    prefix = parse_string(request.args.get('prefix'))
    last_name = parse_string(request.args.get('lastName'))
    limit = get_limit()

    report_list = reports.fetch_reports_by_name(g.owner_id, prefix, last_name, limit)

    r = ApiResponse(200)
    r.result = [OrderedDict([('name', report.report_name),
                             ('href', href('/reports/%s' % report.report_name))])
                for report in report_list]

    if len(report_list) == limit:
        r.set_detail('next', set_query_param(request.url, 'lastName',
                                             report_list[-1][ 'report_name']))
    else:
        r.set_detail('next', None)

    return r.get()

def _report_instance_desc(report_name, ri, expand, expand_input):
    desc = ri.desc(expand, expand_input)
    desc['href'] = href('/reports/%s/instances/%s' % (report_name,
                                                      ri.report_instance_id.hex))
    return desc

@bp_api.route('/reports/<name>/instances', methods=['GET'])
def get_report_instances(name):
    from_dt = parse_datetime(request.args.get('from'))
    to_dt = parse_datetime(request.args.get('to'))
    tags = parse_tags(request.args.get('tags'))

    expand = parse_bool(request.args.get('expand'))
    if expand is None:
        expand = True

    expand_input = parse_bool(request.args.get('expandInput')) or False
    limit = get_limit()
    from_id = parse_id(request.args.get('fromId'))
    last_id = parse_id(request.args.get('lastId'))
    order = parse_enum(request.args.get('order'), ('asc', 'desc')) or 'asc'

    report = get_report(name)

    after = None
    before = None
    if last_id:
        if order == 'asc':
            after = last_id
            before = None
        elif order == 'desc':
            after = None
            before = last_id
    elif from_id:
        if order == 'asc':
            after = uuid_for_prev_dt(from_id)
            before = None
        elif order == 'desc':
            after = None
            before = uuid_for_next_dt(from_id)

    instances = report.fetch_instances(from_dt=from_dt, to_dt=to_dt, limit=limit, tags=tags,
                                       order=order, after=after, before=before)

    res = [_report_instance_desc(name, ri, expand, expand_input) for ri in instances]
    r = ApiResponse(200, result=res)
    if len(instances) == limit:
        r.set_detail('next', set_query_param(request.url, 'lastId',
                                             to_id(instances[-1].report_instance_id)))
    else:
        r.set_detail('next', None)
    return r.get()


@bp_api.route('/reports/<name>/instances/<id>', methods=['GET'])
def get_single_report_instance(name, id):
    report_instance_id = parse_id(id)

    report = get_report(name)
    ri = report.fetch_single_instance(report_instance_id)
    if not ri:
        return ApiResponse(404, message='Report instance with id <%s> not found' % to_id(report_instance_id)).get()
    return ApiResponse(200, result=_report_instance_desc(name, ri, True, True)).get()


@bp_api.route('/reports/<name>/instances/<id>', methods=['DELETE'])
def delete_single_report_instance(name, id):
    report_instance_id = parse_id(id)
    report = get_report(name)
    report.delete_single_instance(report_instance_id)
    return ApiResponse(200).get()

def format_from_headers():
    try:
        if not request.mimetype:
            return None
        if '/' in request.mimetype:
            mformat = request.mimetype.split('/')[1]
        else:
            mformat = request.mimetype
        mformat = mformat.strip().lower()
        if mformat in ('json', 'csv', 'markdown'):
            return mformat
        return None
    except:
        return None

@bp_api.route('/reports/<name>', methods=['POST'])
def post_report_instance(name):
    form_key = request.args.get('formKey')
    if form_key:
        input_string = request.form.get(form_key)
    else:
        input_string = request.get_data()

    tags = parse_tags(request.args.get('tags'))
    created = parse_datetime(request.args.get('created'))
    input_type = parse_enum(request.args.get('format'),
                         [k for k in parseany.INPUT_PARSERS if not k.startswith('_')]) \
                or format_from_headers() \
                or 'any'
    force_header = parse_int_tags(request.args.get('header'))
    delimiter = parse_string(request.args.get('delimiter'))
    autotags = parse_enum(request.args.get('autotags'), ['ip'])
    link = parse_string(request.args.get('link'))

    ### check for empty input
    if not input_string or input_string.isspace():
        return ApiResponse(422, message='Empty report data', error_code='ERROR_EMPTY_REPORT_DATA').get()

    ### autotags
    if autotags and 'ip' in autotags:
        if (not tags) or 'ip' not in tags:
            tags = tags or []
            ip_address = client_ip()
            if ip_address:
                tags.append('ip:%s' % ip_address)

    if tags:
        if len(tags) > mqeconfig.MAX_TAGS:
            return bad_request('Too many tags, maximum is %s' % mqeconfig.MAX_TAGS).get()
        if any(len(t) > apiconfig.SIMPLE_VALUE_LEN_LIMIT for t in tags):
            return bad_request('Tag value too long').get()

    if delimiter:
        if len(delimiter) > apiconfig.SIMPLE_VALUE_LEN_LIMIT:
            return bad_request('Delimiter value too long').get()

    if link:
        if len(link) > apiconfig.USER_VALUE_LEN_LIMIT:
            return bad_request('Link value too long').get()

    ip_options = {
        'delimiter': delimiter
    }

    # select or create report, check name validity
    if not name:
        return bad_request('Empty report name').get()
    if len(name) > apiconfig.SIMPLE_VALUE_LEN_LIMIT:
        return bad_request('Report name too long').get()
    report = reports.Report.select_or_insert(g.owner_id, name)
    if not report:
        return bad_request('Could not get report').get()

    if link:
        extra_ri_data = {
            'link': link,
        }
    else:
        extra_ri_data = None

    ipres = report.process_input(input_string, tags=tags, created=created, input_type=input_type,
                                 ip_options=ip_options, force_header=force_header, extra_ri_data=extra_ri_data)

    if ipres.report_instance is None:
        message = 'Cannot parse input'
        if input_type != 'any':
            message += ' using format %s' % input_type
        return ApiResponse(400, message=message).get()

    return ApiResponse(200, result=_report_instance_desc(
        name, ipres.report_instance, True, False)).get()

