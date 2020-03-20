# coding=utf-8

from gspider.spider import Spider
from gspider.http import HttpRequest
from gspider.run import run_spider
from gspider.extension import Extension


class FooError(Exception):
    pass


class HandlerDownloaderMiddleware(Extension):
    def handle_request(self, request):
        if request.url.endswith('error'):
            raise FooError


class HandlerSpiderMiddleware(Extension):
    def handle_spider_input(self, response):
        if response.request.url.endswith('not-found'):
            raise FooError

    def handle_spider_error(self, response, error):
        if isinstance(error, FooError):
            return ()


class HandlerSpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = self.config.get('data')
        self.server_address = self.config.get('server_address')

    def start_requests(self):
        yield HttpRequest("http://unknown/", errback=self.error_back)
        yield HttpRequest("http://{}/error".format(self.server_address), errback=self.handle_request_error)
        yield HttpRequest("http://{}/".format(self.server_address), dont_filter=True)
        yield HttpRequest("http://{}/".format(self.server_address), dont_filter=True, callback=self.generator_parse)
        yield HttpRequest("http://{}/".format(self.server_address), dont_filter=True, callback=self.func_prase)
        yield HttpRequest("http://{}/".format(self.server_address), dont_filter=True, callback=self.return_list_parse)
        yield HttpRequest("http://{}/".format(self.server_address), dont_filter=True, callback=self.return_none_parse)

    def parse(self, response):
        self.data.add('parse')

    def error_back(self, request, err):
        self.data.add('error_back')
        raise RuntimeError('not an error actually')

    def handle_request_error(self, request, error):
        assert isinstance(error, FooError)
        self.data.add('handle_request_error')

    def generator_parse(self, response):
        self.data.add('generator_parse')
        if response.status / 100 != 2:
            raise RuntimeError('not an error actually')
        # it will never come here
        yield None

    def func_prase(self, response):
        self.data.add('func_parse')
        raise RuntimeError('not an error actually')

    def return_list_parse(self, response):
        self.data.add('return_list_parse')
        return []

    def return_none_parse(self, response):
        self.data.add('return_none_parse')


def test_spider_handlers():
    data = set()
    run_spider(HandlerSpider, log_level='DEBUG', extensions=[HandlerDownloaderMiddleware, HandlerSpiderMiddleware],
               data=data, server_address='python.org')
    assert 'parse' in data
    assert 'error_back' in data
    assert 'handle_request_error' in data
    assert 'generator_parse' in data
    assert 'func_parse' in data
    assert 'return_list_parse' in data
    assert 'return_none_parse' in data
