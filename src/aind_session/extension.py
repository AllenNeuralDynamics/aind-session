from __future__ import annotations

import logging
from typing import Callable

from typing_extensions import TypeVar

import aind_session.session
import aind_session.utils.codeocean_utils

logger = logging.getLogger(__name__)


_reserved_namespaces: set[str] = set()

NS = TypeVar("NS")


def register_namespace(name: str) -> Callable[[type[NS]], type[NS]]:
    """
    Decorator for registering custom functionality with a Session object.

    Copied from https://github.com/pola-rs/polars/blob/py-1.5.0/py-polars/polars/api.py#L124-L219
    """
    return _create_namespace(name, aind_session.session.Session)


class ExtensionBaseClass:
    """A baseclass with init and repr. Subclass to add modalities etc. to the
    Session class, and use the `register_namespace` decorator."""

    def __init__(self, session: aind_session.session.Session) -> None:
        self._session = session

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._session})"


class NameSpace:
    """Establish property-like namespace object for user-defined functionality.

    From https://docs.pola.rs/api/python/stable/reference/api.html
    """

    def __init__(self, name: str, namespace: type[NS]) -> None:
        self._accessor = name
        self._ns = namespace

    def __get__(self, instance: NS | None, cls: type[NS]) -> NS | type[NS]:
        if instance is None:
            return self._ns  # type: ignore[return-value]

        ns_instance = self._ns(instance)  # type: ignore[call-arg]
        setattr(instance, self._accessor, ns_instance)
        return ns_instance  # type: ignore[return-value]


def _create_namespace(
    name: str, cls: type[aind_session.session.Session]
) -> Callable[[type[NS]], type[NS]]:
    """Register custom namespace against the underlying class.

    Copied from https://github.com/pola-rs/polars/blob/d0475d7b6502cdc80317dc8795200c615d151a35/py-polars/polars/api.py#L48
    """

    def namespace(ns_class: type[NS]) -> type[NS]:
        if name in _reserved_namespaces:
            raise AttributeError(f"cannot override reserved namespace {name!r}")
        elif hasattr(cls, name):
            logger.warning(
                f"Overriding existing custom namespace {name!r} (on {cls.__name__!r})",
            )

        setattr(cls, name, NameSpace(name, ns_class))
        return ns_class

    return namespace
