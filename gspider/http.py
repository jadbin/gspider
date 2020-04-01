# coding=utf-8

import inspect

from requests.models import Response

from gspider.utils import get_encoding_from_content, get_encoding_from_content_type


class HttpRequest:
    def __init__(self, url, method="GET", params=None, body=None, json=None, headers=None, proxies=None,
                 timeout=20, verify_ssl=None, allow_redirects=None, auth=None,
                 priority=None, dont_filter=False, callback=None, errback=None, meta=None):
        """
        Construct an HTTP request.
        """
        self.url = url
        self.params = params
        self.method = method
        self.body = body
        self.json = json
        self.headers = headers
        self.proxies = proxies
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.allow_redirects = allow_redirects
        self.auth = auth
        self.priority = priority
        self.dont_filter = dont_filter
        self.callback = callback
        self.errback = errback
        self._meta = dict(meta) if meta else {}

    def __str__(self):
        return '<{}, {}>'.format(self.method, self.url)

    __repr__ = __str__

    @property
    def meta(self):
        return self._meta

    def copy(self):
        return self.replace()

    def replace(self, **kwargs):
        for i in ["url", "method", "params", "body", "json", "headers", "proxies",
                  "timeout", "verify_ssl", "allow_redirects", "auth",
                  "priority", "dont_filter", "callback", "errback", "meta"]:
            kwargs.setdefault(i, getattr(self, i))
        return type(self)(**kwargs)

    def to_dict(self):
        callback = self.callback
        if inspect.ismethod(callback):
            callback = callback.__name__
        errback = self.errback
        if inspect.ismethod(errback):
            errback = errback.__name__
        d = {
            'url': self.url,
            'method': self.method,
            'body': self.body,
            'headers': self.headers,
            'proxy': self.proxy,
            'timeout': self.timeout,
            'verify_ssl': self.verify_ssl,
            'allow_redirects': self.allow_redirects,
            'auth': self.auth,
            'proxy_auth': self.proxy_auth,
            'priority': self.priority,
            'dont_filter': self.dont_filter,
            'callback': callback,
            'errback': errback,
            'meta': self.meta
        }
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


class HttpResponse:
    def __init__(self, request=None, response: Response = None):
        """
        Construct an HTTP response.
        """
        self.request = request
        self.response = response
        self._encoding = None

    def __str__(self):
        return '<{}, {}>'.format(self.status, self.url)

    __repr__ = __str__

    @property
    def url(self):
        if self.response:
            return self.response.url

    @property
    def status(self):
        if self.response:
            return self.response.status_code

    @property
    def body(self):
        if self.response:
            return self.response.content

    @property
    def text(self):
        if self._encoding is None:
            encoding = get_encoding_from_content_type(self.response.headers.get("Content-Type"))
            if not encoding and self.response.content:
                encoding = get_encoding_from_content(self.response.content)
            encoding = encoding or 'utf-8'
            self._encoding = encoding
            self.response.encoding = encoding
        return self.response.text

    @property
    def meta(self):
        if self.request:
            return self.request.meta
