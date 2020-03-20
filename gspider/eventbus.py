# coding=utf-8

import weakref
import logging

log = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self._refs = {}

    def subscribe(self, receiver, event):
        if event not in self._refs:
            self._refs[event] = {}
        if not hasattr(receiver, '__func__') or not hasattr(receiver, '__self__'):
            raise ValueError("Failed to subscribe, {} has no attribute '__func__' or '__self__'".format(receiver))
        i = self._calc_id(receiver)
        if i in self._refs[event]:
            f = self._refs[event][i]()
            if f is not None:
                return
        self._refs[event][i] = weakref.WeakMethod(receiver)

    def unsubscribe(self, receiver, event):
        if event in self._refs:
            i = self._calc_id(receiver)
            if i in self._refs[event]:
                del self._refs[event][i]

    def send(self, event, **kwargs):
        if event not in self._refs:
            return
        del_list = []
        for i in self._refs[event]:
            f = self._refs[event][i]()
            if f is None:
                del_list.append(i)
            else:
                try:
                    f(**kwargs)
                except Exception:
                    log.error("Failed to send the event", exc_info=True)
        for i in del_list:
            del self._refs[event][i]
        del del_list

    def _calc_id(self, receiver):
        return hash((id(receiver.__func__), id(receiver.__self__)))
