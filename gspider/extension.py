# coding=utf-8

import logging

from .utils import load_object, isiterable
from . import events
from .errors import NotEnabled
from .http import HttpRequest, HttpResponse

log = logging.getLogger(__name__)


class ExtensionManager:
    def __init__(self, *extensions):
        self.extensions = []
        for ext in extensions:
            self._add_extension(ext)

    @classmethod
    def from_crawler(cls, crawler):
        ext_list = cls._extension_list_from_config(crawler.config)
        exts = []
        for cls_path in ext_list:
            ext_cls = load_object(cls_path)
            try:
                if hasattr(ext_cls, "from_crawler"):
                    ext = ext_cls.from_crawler(crawler)
                else:
                    ext = ext_cls()
            except NotEnabled:
                log.debug('%s is not enabled', cls_path)
            else:
                exts.append(ext)
        obj = cls(*exts)
        crawler.event_bus.subscribe(obj.open, events.crawler_start)
        crawler.event_bus.subscribe(obj.close, events.crawler_shutdown)
        return obj

    def _add_extension(self, ext):
        assert isinstance(ext, Extension)
        self.extensions.append(ext)

    @classmethod
    def _extension_list_from_config(cls, config):
        return cls._make_component_list('extensions', config)

    @staticmethod
    def _list_from_config(name, config):
        c = config.get(name)
        assert c is None or isinstance(c, list), \
            "'{}' must be None or a list, got {}".format(name, type(c).__name__)
        if c is None:
            return []
        return c

    @classmethod
    def _make_component_list(cls, name, config):
        c_base = cls._list_from_config('default_' + name, config)
        c = cls._list_from_config(name, config)
        return c + c_base

    def open(self):
        for ext in self.extensions:
            ext.open()

    def close(self):
        for ext in self.extensions:
            ext.close()

    def handle_request(self, request):
        for ext in self.extensions:
            res = ext.handle_request(request)
            assert res is None or isinstance(res, (HttpRequest, HttpResponse)), \
                "Request handler must return None, HttpRequest or HttpResponse, got {}".format(type(res).__name__)
            if res:
                return res

    def handle_response(self, request, response):
        for ext in self.extensions:
            res = ext.handle_response(request, response)
            assert res is None or isinstance(res, HttpRequest), \
                "Response handler must return None or HttpRequest, got {}".format(type(res).__name__)
            if res:
                return res

    def handle_error(self, request, error):
        for ext in self.extensions:
            res = ext.handle_error(request, error)
            assert res is None or isinstance(res, (HttpRequest, HttpResponse)), \
                "Exception handler must return None, HttpRequest or HttpResponse, got {}".format(type(res).__name__)
            if res:
                return res
        return error

    def handle_spider_input(self, response):
        for ext in self.extensions:
            res = ext.handle_spider_input(response)
            assert res is None, \
                "Spider input handler must return None, got {}".format(type(res).__name__)

    def handle_spider_output(self, response, result):
        for ext in self.extensions:
            result = ext.handle_spider_output(response, result)
            assert isiterable(result), \
                "Spider output handler must return an iterable object, got {}".format(type(result).__name__)
        return result

    def handle_spider_error(self, response, error):
        for ext in self.extensions:
            res = ext.handle_spider_error(response, error)
            assert res is None or isiterable(res), \
                "Spider exception handler must return None or an iterable object, got {}".format(type(res).__name__)
            if res is not None:
                return res
        return error

    def handle_start_requests(self, result):
        for ext in self.extensions:
            result = ext.handle_start_requests(result)
            assert isiterable(result), \
                "Start requests handler must return an iterable object, got {}".format(type(result).__name__)
        return result


class Extension:
    def open(self):
        pass

    def close(self):
        pass

    def handle_request(self, request):
        pass

    def handle_response(self, request, response):
        pass

    def handle_error(self, request, error):
        pass

    def handle_spider_input(self, response):
        pass

    def handle_spider_output(self, response, result):
        return result

    def handle_spider_error(self, response, error):
        pass

    def handle_start_requests(self, result):
        return result
