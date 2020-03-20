# coding=utf-8

import json

import pytest

from gspider.http import HttpRequest
from gspider.fetcher import Fetcher
from gspider.errors import HttpError


def test_basic_auth():
    fetcher = Fetcher()

    def no_auth():
        req = HttpRequest("http://httpbin.org/basic-auth/user/passwd")
        with pytest.raises(HttpError) as e:
            fetcher.fetch(req)
            assert e.value.response.status == 401

    def tuple_auth():
        req = HttpRequest("http://httpbin.org/basic-auth/user/passwd")
        req.auth = ('user', 'passwd')
        resp = fetcher.fetch(req)
        assert resp.status == 200

    no_auth()
    tuple_auth()


def test_params():
    fetcher = Fetcher()

    def query_params():
        url = "http://httpbin.org/anything?key=value&none="
        resp = fetcher.fetch(HttpRequest(url))
        assert json.loads(resp.text)['args'] == {'key': 'value', 'none': ''}

    def dict_params():
        resp = fetcher.fetch(
            HttpRequest("http://httpbin.org/get", params={'key': 'value', 'none': ''}))
        assert json.loads(resp.text)['args'] == {'key': 'value', 'none': ''}

    def list_params():
        resp = fetcher.fetch(HttpRequest("http://httpbin.org/get",
                                         params=[('list', '1'), ('list', '2')]))
        assert json.loads(resp.text)['args'] == {'list': ['1', '2']}

    query_params()
    dict_params()
    list_params()


def test_headers():
    fetcher = Fetcher()
    headers = {'User-Agent': 'gspider'}
    resp = fetcher.fetch(HttpRequest("http://httpbin.org/get",
                                     headers=headers))
    assert resp.status == 200
    data = json.loads(resp.text)['headers']
    assert 'User-Agent' in data and data['User-Agent'] == 'gspider'


def test_body():
    fetcher = Fetcher()

    def post_bytes():
        bytes_data = 'bytes data: 字节数据'
        resp = fetcher.fetch(HttpRequest('http://httpbin.org/post',
                                         'POST', body=bytes_data.encode(),
                                         headers={'Content-Type': 'text/plain'}))
        assert resp.status == 200
        body = json.loads(resp.text)['data']
        assert body == bytes_data

    post_bytes()


def test_allow_redirects():
    fetcher = Fetcher()

    resp = fetcher.fetch(HttpRequest('http://httpbin.org/redirect-to',
                                     params={'url': 'http://python.org'}))
    assert resp.status // 100 == 2 and 'python.org' in resp.url

    resp = fetcher.fetch(HttpRequest('http://httpbin.org/redirect-to',
                                     params={'url': 'http://python.org'},
                                     allow_redirects=False))
    assert resp.status // 100 == 3
