# coding=utf-8

import os
import hashlib
import logging
from importlib import import_module
from os.path import isfile
import re
import cgi

from urllib.parse import urlsplit, parse_qsl, urlencode


def load_object(path):
    if isinstance(path, str):
        dot = path.rindex(".")
        module, name = path[:dot], path[dot + 1:]
        mod = import_module(module)
        return getattr(mod, name)
    return path


default_log_level = 'info'
default_log_format = '%(asctime)s %(name)s [%(levelname)s] %(message)s'
default_log_date_format = '[%Y-%m-%d %H:%M:%S %z]'


def configure_logger(name, level=None, format=None, date_format=None, file=None):
    if level is None:
        level = default_log_level
    if format is None:
        format = default_log_format
    if date_format is None:
        date_format = default_log_date_format

    level = level.upper()
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if file:
        handler = logging.FileHandler(file)
    else:
        handler = logging.StreamHandler()
    formatter = logging.Formatter(format, date_format)
    handler.setFormatter(formatter)
    logger.handlers.clear()
    logger.addHandler(handler)
    return logger


def to_bytes(data, encoding=None):
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        return data.encode(encoding or "utf-8")
    raise TypeError("Need bytes or str, got {}".format(type(data).__name__))


def iterable_to_list(gen):
    res = []
    if gen is not None:
        for r in gen:
            res.append(r)
    return res


def daemonize():
    if os.fork():
        os._exit(0)
    os.setsid()
    if os.fork():
        os._exit(0)
    os.umask(0o22)
    os.closerange(0, 3)
    fd_null = os.open(os.devnull, os.O_RDWR)
    if fd_null != 0:
        os.dup2(fd_null, 0)
    os.dup2(fd_null, 1)
    os.dup2(fd_null, 2)


def load_config(fname):
    if fname is None or not isfile(fname):
        raise ValueError('{} is not a file'.format(fname))
    code = compile(open(fname, 'rb').read(), fname, 'exec')
    cfg = {
        "__builtins__": __builtins__,
        "__name__": "__config__",
        "__file__": fname,
        "__doc__": None,
        "__package__": None
    }
    exec(code, cfg, cfg)
    return cfg


def iter_settings(config):
    for key, value in config.items():
        if not key.startswith('_'):
            yield key, value


def isiterable(obj):
    return hasattr(obj, "__iter__")


def cmp(a, b):
    return (a > b) - (a < b)


def request_fingerprint(request):
    sha1 = hashlib.sha1()
    sha1.update(to_bytes(request.method))
    res = urlsplit(request.url)
    queries = parse_qsl(res.query)
    queries.sort()
    final_query = urlencode(queries)
    sha1.update(to_bytes('{}://{}{}:{}?{}'.format(res.scheme,
                                                  '' if res.hostname is None else res.hostname,
                                                  res.path,
                                                  80 if res.port is None else res.port,
                                                  final_query)))
    sha1.update(request.body or b'')
    return sha1.hexdigest()


def get_encoding_from_content_type(content_type):
    if content_type:
        content_type, params = cgi.parse_header(content_type)
        if "charset" in params:
            return params["charset"]


_charset_flag = re.compile(r"""<meta.*?charset=["']*(.+?)["'>]""", flags=re.I)
_pragma_flag = re.compile(r"""<meta.*?content=["']*;?charset=(.+?)["'>]""", flags=re.I)
_xml_flag = re.compile(r"""^<\?xml.*?encoding=["']*(.+?)["'>]""")


def get_encoding_from_content(content):
    if isinstance(content, bytes):
        content = content.decode("ascii", errors="ignore")
    elif not isinstance(content, str):
        raise ValueError("content should be bytes or str")
    s = _charset_flag.search(content)
    if s:
        return s.group(1).strip()
    s = _pragma_flag.search(content)
    if s:
        return s.group(1).strip()
    s = _xml_flag.search(content)
    if s:
        return s.group(1).strip()
