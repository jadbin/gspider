# coding=utf-8

import logging
import inspect

import gevent

from .http import HttpRequest, HttpResponse
from .errors import IgnoreRequest, StopCrawler, ClientError, HttpError
from .spider import Spider
from .eventbus import EventBus
from . import events
from .extension import ExtensionManager
from .utils import load_object, iterable_to_list, isiterable

log = logging.getLogger(__name__)


class Crawler:
    def __init__(self, config):
        self.config = config
        self.event_bus = EventBus()
        self.queue = self._instance_from_crawler(self.config.get('queue'))
        self.dupe_filter = self._instance_from_crawler(self.config.get('dupe_filter'))
        self.fetcher = self._instance_from_crawler(self.config.get('fetcher'))
        self.spider = self._instance_from_crawler(self.config.get('spider'))
        assert isinstance(self.spider, Spider), 'spider must inherit from the Spider class'
        log.info('Spider class: %s', self.spider.__class__.__name__)
        self.extension = ExtensionManager.from_crawler(self)
        log.info('Extensions: %s', self._log_objects(self.extension.extensions))

    def start_requests(self):
        try:
            res = self.spider.start_requests()
            assert res is None or isiterable(res), \
                "Start requests must be None or an iterable object, got {}".format(type(res).__name__)
            result = iterable_to_list(res)
            if result:
                res = self.extension.handle_start_requests(result)
                result = iterable_to_list(res)
        except StopCrawler:
            raise
        except Exception:
            log.error("Failed to get start requests", exc_info=True)
        else:
            return result

    def schedule(self, request):
        try:
            res = self.dupe_filter.is_duplicated(request)
            if not res:
                self.event_bus.send(events.request_scheduled, request=request)
                self.queue.push(request)
        except StopCrawler:
            raise
        except Exception:
            log.error('Failed to schedule %s', request, exc_info=True)

    def next_request(self):
        req = self.queue.pop()
        return req

    def fetch(self, req):
        try:
            resp = self._fetch(req)
        except StopCrawler:
            raise
        except Exception as e:
            if isinstance(e, IgnoreRequest):
                self.event_bus.send(events.request_ignored, request=req, error=e)
            elif isinstance(e, (ClientError, HttpError)):
                log.info('Failed to make %s: %s', req, e)
            else:
                log.warning("Failed to request %s", req, exc_info=True)
            self.spider.handle_error(req, e)
        else:
            self._handle_response(resp)

    def _fetch(self, req):
        try:
            res = self.extension.handle_request(req)
            if isinstance(res, HttpRequest):
                return res
            if res is None:
                res = self.fetcher.fetch(req)
        except StopCrawler:
            raise
        except Exception as e:
            res = self.extension.handle_error(req, e)
            if isinstance(res, Exception):
                raise res
        if isinstance(res, HttpResponse):
            _res = self.extension.handle_response(req, res)
            if _res:
                res = _res
            # bind request
            res.request = req
        return res

    def _handle_response(self, resp):
        if isinstance(resp, HttpRequest):
            self.schedule(resp)
        elif isinstance(resp, HttpResponse):
            self.event_bus.send(events.response_received, response=resp)
            try:
                result = self._parse(resp)
            except StopCrawler:
                raise
            except Exception as e:
                if isinstance(e, IgnoreRequest):
                    self.event_bus.send(events.request_ignored, request=resp.request, error=e)
                else:
                    log.warning("Failed to parse %s", resp, exc_info=True)
            else:
                for r in result:
                    self._handle_parsing_result(r)

    def _parse(self, response):
        request = response.request
        try:
            try:
                self.extension.handle_spider_input(response)
            except Exception as e:
                self.spider.handle_error(request, e)
                raise e
            res = self.spider.handle_response(response)
            assert res is None or isiterable(res), \
                "Parsing result must be None or an iterable object, got {}".format(type(res).__name__)
            result = iterable_to_list(res)
        except Exception as e:
            res = self.extension.handle_spider_error(response, e)
            if isinstance(res, Exception):
                raise res
            result = iterable_to_list(res)
        if result:
            res = self.extension.handle_spider_output(response, result)
            result = iterable_to_list(res)
        return result

    def _handle_parsing_result(self, result):
        if isinstance(result, HttpRequest):
            self.schedule(result)

    def _instance_from_crawler(self, cls_path):
        obj_cls = load_object(cls_path)
        if inspect.isclass(obj_cls):
            if hasattr(obj_cls, "from_crawler"):
                obj = obj_cls.from_crawler(self)
            else:
                obj = obj_cls()
        else:
            obj = obj_cls
        return obj

    @staticmethod
    def _log_objects(objects):
        if objects:
            return ''.join(['\n\t({}/{}) {}'.format(i + 1, len(objects), o) for i, o in enumerate(objects)])
        return ''


class CrawlerRunner:
    def __init__(self, crawler):
        self.crawler = crawler

        self._workers = None
        self._req_in_worker = None
        self._start_requests_generator = None
        self._is_running = False

    def run(self):
        if self._is_running:
            return
        self._is_running = True

        self.crawler.event_bus.send(events.crawler_start)
        max_workers = self.crawler.config.getint('max_workers')
        assert max_workers > 0, 'max workers should > 0'
        log.info("The maximum number of workers: %s", max_workers)

        self._start_requests_generator = gevent.spawn(self._schedule_start_requests)
        self._workers = []
        for i in range(max_workers):
            self._workers.append(gevent.spawn(self._fetch, i))
        self._req_in_worker = [None] * max_workers

        log.info('Crawler is running')
        gevent.joinall([self._start_requests_generator] + self._workers)
        self.crawler.event_bus.send(events.crawler_shutdown)
        log.info('Crawler is stopped')

        self._start_requests_generator = None
        self._workers = None
        self._req_in_worker = None

    def stop(self):
        if not self._is_running:
            return
        self._is_running = False
        self._shutdown()

    def _shutdown(self):
        log.info("Shutdown now")
        self._start_requests_generator.kill(exception=StopCrawler, block=False)
        for w in self._workers:
            w.kill(exception=StopCrawler, block=False)

    def _all_done(self):
        if self._start_requests_generator.ready() and len(self.crawler.queue) <= 0:
            no_active = True
            for i in range(len(self._workers)):
                if self._req_in_worker[i]:
                    no_active = False
                    break
            return no_active
        return False

    def _schedule_start_requests(self):
        try:
            reqs = self.crawler.start_requests()
            for r in reqs:
                self.crawler.schedule(r)
        except StopCrawler:
            pass

    def _fetch(self, coro_id):
        try:
            while True:
                req = self.crawler.next_request()
                log.debug("%s -> worker[%s]", req, coro_id)
                self._req_in_worker[coro_id] = req
                try:
                    self.crawler.fetch(req)
                except StopCrawler:
                    self.stop()
                    raise
                self._req_in_worker[coro_id] = None
                # check if it's all done
                if self._all_done():
                    self.stop()
        except StopCrawler:
            pass
