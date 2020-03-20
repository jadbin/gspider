# coding=utf-8

import logging

import requests
from requests import HTTPError, Response
import gevent

from .errors import ClientError, HttpError
from .http import HttpRequest, HttpResponse

log = logging.getLogger(__name__)


class Fetcher:
    default_session_id = '0'

    def __init__(self, default_headers=None, verify_ssl=None, proxies=None):
        self.default_headers = default_headers
        self.verify_ssl = verify_ssl
        self.proxies = proxies
        self.sessions = {}

    def new_session(self):
        session = requests.Session()
        if self.default_headers is not None:
            session.headers.update(self.default_headers)
        if self.verify_ssl is not None:
            session.verify = self.verify_ssl
        if self.proxies is not None:
            session.proxies = self.proxies
        return session

    def close_session(self, session_id):
        if session_id in self.sessions:
            session = self.sessions.pop(session_id)
            session.close()

    @classmethod
    def from_crawler(cls, crawler):
        config = crawler.config
        kwargs = {}
        if config['verify_ssl'] is not None:
            kwargs['verify_ssl'] = config['verify_ssl']
        if config['proxies'] is not None:
            kwargs['proxies'] = config['proxies']
        return cls(**kwargs)

    def fetch(self, request: HttpRequest):
        log.debug("HTTP request: %s", request)
        try:
            session = self._get_session()
            kwargs = {}
            if request.params is not None:
                kwargs['params'] = request.params
            if request.body is not None:
                kwargs['data'] = request.body
            if request.json is not None:
                kwargs['json'] = request.json
            if request.headers is not None:
                kwargs['headers'] = request.headers
            if request.auth is not None:
                kwargs['auth'] = request.auth
            if request.timeout is not None:
                kwargs['timeout'] = request.timeout
            if request.allow_redirects is not None:
                kwargs['allow_redirects'] = request.allow_redirects
            if request.proxies is not None:
                kwargs['proxies'] = request.proxies
            if request.verify_ssl is not None:
                kwargs['verify'] = request.verify_ssl
            resp = session.request(request.method, request.url, **kwargs)
            resp.raise_for_status()
            response = self._make_response(resp, request)
        except HTTPError as e:
            raise HttpError('{}'.format(e.response),
                            response=self._make_response(e.response, request))
        except Exception as e:
            raise ClientError(e)
        log.debug("HTTP response: %s", response)
        return response

    def _make_response(self, response: Response, request: HttpRequest):
        return HttpResponse(request=request, response=response)

    def _get_session(self):
        try:
            g = gevent.getcurrent().minimal_ident
        except AttributeError:
            g = 0
        if g not in self.sessions:
            self.sessions[g] = self.new_session()
        return self.sessions[g]
