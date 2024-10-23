from __future__ import annotations

import logging
from typing import Any, Callable

from typing_extensions import TypeVar

import aind_session.session
import aind_session.utils.codeocean_utils

logger = logging.getLogger(__name__)


_reserved_namespaces: set[str] = set()

_NS = TypeVar("_NS")


def register_namespace(
    name: str, cls: type = aind_session.session.Session
) -> Callable[[type[_NS]], type[_NS]]:
    """
    Decorator for registering custom functionality with Session or Subject objects.

    Copied from https://github.com/pola-rs/polars/blob/py-1.5.0/py-polars/polars/api.py#L124-L219
    """
    return _create_namespace(name, cls)


class ExtensionBaseClass:
    """A convenience baseclass with init, repr and a single property: `_base`,
    which links to the base instance from which the extension was created.

    Subclass this baseclass to add a namespace to the Session or Subject class, which can
    then be accessed on all new instances.

    Examples
    --------
    Create a custom namespace by subclassing ExtensionBaseClass and registering it with the Session class:
    >>> @aind_session.register_namespace("my_extension", aind_session.Session)
    ... class MyExtension(aind_session.ExtensionBaseClass):
    ...
    ...    constant = 42
    ...
    ...    @classmethod
    ...    def add(cls, value) -> int:
    ...        return cls.constant + value
    ...
    ...    # Access the underlying session object with self._base
    ...    @property
    ...    def oldest_data_asset_id(self) -> str:
    ...        return min(self._base.data_assets, key=lambda x: x.created).id
    ...

    Create a session object and access the custom namespace:
    >>> session = aind_session.Session("ecephys_676909_2023-12-13_13-43-40")
    >>> session.my_extension.constant
    42
    >>> session.my_extension.add(10)
    52
    >>> session.my_extension.oldest_data_asset_id
    '16d46411-540a-4122-b47f-8cb2a15d593a'
    """

    def __init__(self, base: Any) -> None:
        self._base = base

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._base})"


class _NameSpace:
    """Establish property-like namespace object for user-defined functionality.

    From https://docs.pola.rs/api/python/stable/reference/api.html
    """

    def __init__(self, name: str, namespace: type[_NS]) -> None:
        self._accessor = name
        self._ns = namespace

    def __get__(self, instance: _NS | None, cls: type[_NS]) -> _NS | type[_NS]:
        if instance is None:
            return self._ns  # type: ignore[return-value]

        ns_instance = self._ns(instance)  # type: ignore[call-arg]
        setattr(instance, self._accessor, ns_instance)
        return ns_instance  # type: ignore[return-value]


def _create_namespace(name: str, cls: type) -> Callable[[type[_NS]], type[_NS]]:
    """Register custom namespace against the underlying class.

    Copied from https://github.com/pola-rs/polars/blob/d0475d7b6502cdc80317dc8795200c615d151a35/py-polars/polars/api.py#L48
    """

    def namespace(ns_class: type[_NS]) -> type[_NS]:
        if name in _reserved_namespaces:
            raise AttributeError(f"cannot override reserved namespace {name!r}")
        elif hasattr(cls, name):
            logger.warning(
                f"Overriding existing custom namespace {name!r} (on {cls.__name__!r})",
            )

        setattr(cls, name, _NameSpace(name, ns_class))
        return ns_class

    return namespace


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
