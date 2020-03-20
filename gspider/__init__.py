# coding=utf-8

from . import _patch
from .http import HttpRequest, HttpResponse
from .fetcher import Fetcher
from .spider import Spider
from .selector import Selector
from .run import run_spider, make_requests
from .errors import StopCrawler

__all__ = ['HttpRequest', 'HttpResponse',
           'Fetcher',
           'Spider',
           'Selector',
           'run_spider', 'make_requests',
           'StopCrawler']

__version__ = '0.1.0'

del _patch
