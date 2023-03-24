from __future__ import annotations

from typing import Dict, Callable, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from .generic_viewer_frontend import GenericViewerFrontend
    from .generic_viewer_backend import GenericViewerBackend

from . import backend_utils as buts
from . import frontend_utils as futs

from abc import ABC, abstractmethod
import os

_CORES = os.sched_getaffinity(0)  # AMD fix
import pygame.constants as pgmc

os.sched_setaffinity(0, _CORES)  # AMD fix


class BasePlugin(ABC):

    def __init__(self, frontend_obj: GenericViewerFrontend) -> None:

        # The enabled flag is stored internally but not used internally
        # It's for the sake of the frontend & backend to know what to call.
        self.enabled: bool = False

        self.frontend_obj: GenericViewerFrontend = frontend_obj

        self.backend_obj: GenericViewerBackend = None
        self.has_backend: bool = False

        self.shortcut_map: Dict[buts.Shortcut, Callable] = {}

    def register_backend(self, backend_obj: GenericViewerBackend) -> None:

        self.has_backend = True
        self.backend_obj = backend_obj

    def _append_shortcuts(self, subclass_shortcuts: Dict[buts.Shortcut,
                                                         Callable]) -> None:
        '''
        don't subclass this. We're actually gonna be checking that subclass shortcuts don't collide
        with superclass shortcuts.
        '''
        key_set = set(self.shortcut_map.keys())
        extended_key_set = set(subclass_shortcuts.keys())

        if key_set.intersection(extended_key_set):
            raise AssertionError('Shortcut collision.')

        self.shortcut_map.update(subclass_shortcuts)

    @abstractmethod
    def frontend_action(self) -> None:
        '''
            Do computations for this onoff mode
        '''
        pass

    @abstractmethod
    def backend_action(self) -> None:
        '''
            Do the proper graphical stuff in the frontend.
            I kinda don't like that this is in yet-another pygame file, but heck.
        '''
        pass


class OnOffPlugin(BasePlugin):

    def __init__(self, frontend_obj: GenericViewerFrontend, key_onoff: int,
                 modifier_and: int = 0x0) -> None:

        super().__init__(frontend_obj)

        self.shortcut_onoff = buts.Shortcut(key_onoff, modifier_and)

        this_shortcuts = {self.shortcut_onoff: self.toggle}

        self._append_shortcuts(this_shortcuts)

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def toggle(self) -> None:
        if self.enabled:
            self.disable()
        else:
            self.enable()
