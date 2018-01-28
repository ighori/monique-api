from collections import OrderedDict
import json
import unittest

import datetime
import requests

from mqeweb import users

from mqeapi import apiconfig, apiutil


from mqe.dao.daoregistry import register_dao_modules_from_config
register_dao_modules_from_config(apiconfig)


class TestBase(unittest.TestCase):

    def setUp(self):
        self.user = users.User.insert('mqeapitest@example.com', '123')
        users.assign_new_api_key(self.user.user_id)

    def tearDown(self):
        self.user.delete_user()

    def request(self, method, path, **kwargs):
        base_url = apiconfig.BASE_URL_API

        if 'params' not in kwargs:
            kwargs['params'] = {}
        kwargs['params']['key'] = users.select_api_key(self.user.user_id)

        return requests.request(method, '%s/%s' % (base_url, path.lstrip('/')), **kwargs)


class ReportsTest(TestBase):

    def test_post(self):
        d = OrderedDict([('c1', 1), ('c2', 2)])
        r = self.request('POST', '/reports/aaa', data=json.dumps(d))
        self.assertEqual(200, r.status_code)
        self.assertEqual([['c1', 'c2'], [1, 2]], r.json()['result']['rows'])
        self.assertEqual([0], r.json()['result']['header'])
        return r

    def test_get_single(self):
        r_post = self.test_post()
        r = self.request('GET', '/reports/aaa/instances/%s' % r_post.json()['result']['id'])
        self.assertEqual(r_post.json()['result']['rows'], r.json()['result']['rows'])

    def test_get_multi(self):
        self.test_post()
        r_post = self.test_post()

        r = self.request('GET', '/reports/aaa/instances')
        self.assertEqual(2, len(r.json()['result']))
        self.assertEqual(r_post.json()['result']['rows'], r.json()['result'][0]['rows'])
        self.assertEqual(r_post.json()['result']['rows'], r.json()['result'][1]['rows'])
        return r

    def test_delete_single(self):
        r_get = self.test_get_multi()

        r = self.request('DELETE', '/reports/aaa/instances/%s' % r_get.json()['result'][0]['id'])
        self.assertEqual(200, r.status_code)

        r = self.request('GET', '/reports/aaa/instances')
        self.assertEqual(1, len(r.json()['result']))
        self.assertNotEqual(r_get.json()['result'][0]['id'], r.json()['result'][0]['id'])

    def test_get_reports(self):
        self.request('POST', '/reports/a1', data='1')
        self.request('POST', '/reports/a2', data='2')

        r = self.request('GET', '/reports')
        self.assertEqual(['a1', 'a2'], [d['name'] for d in r.json()['result']])

        r = self.request('GET', '/reports?prefix=a2')
        self.assertEqual(['a2'], [d['name'] for d in r.json()['result']])

    def test_delete_multi(self):
        self.test_post()
        r_post = self.test_post()

        r = self.request('GET', '/reports/aaa/instances')
        self.assertEqual(2, len(r.json()['result']))

        r = self.request('DELETE', '/reports/aaa/instances')
        self.assertEqual(200, r.status_code)

        r = self.request('GET', '/reports/aaa/instances')
        self.assertEqual(0, len(r.json()['result']))

    def test_delete_multi_dt(self):
        self.test_post()
        r_post = self.test_post()

        r = self.request('GET', '/reports/aaa/instances?order=asc')
        self.assertEqual(2, len(r.json()['result']))

        self.request('DELETE', '/reports/aaa/instances', params={
            'from': (apiutil.parse_datetime(r.json()['result'][0]['created']) + \
                        datetime.timedelta(microseconds=1)).isoformat(),
        })

        r2 = self.request('GET', '/reports/aaa/instances')
        self.assertEqual([r.json()['result'][0]['id']], [d['id'] for d in r2.json()['result']])

    def test_delete_multi_tags(self):
        r1 = self.request('POST', '/reports/bbb?tags=p1:v1,p2:v2', data='1')
        r2 = self.request('POST', '/reports/bbb?tags=p1:v1,p2:v3', data='2')

        self.request('DELETE', '/reports/bbb/instances?tags=p2:v3')

        self.request('GET', '/reports/bbb/instances')

        r3 = self.request('GET', '/reports/bbb/instances?order=asc')
        self.assertEqual([r1.json()['result']['id']], [d['id'] for d in r3.json()['result']])

