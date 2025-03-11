"""
User-friendly tools for accessing paths, metadata and assets related to AIND sessions.
"""

import doctest
import importlib.metadata
import logging

import npc_io  # ensures .env files are read

# import functions from submodules here:
from aind_session.extension import *
from aind_session.extensions import *
from aind_session.session import *
from aind_session.subject import *
from aind_session.utils import *

logger = logging.getLogger(__name__)

__version__ = importlib.metadata.version("aind_session")
logger.debug(f"{__name__}.{__version__ = }")


def testmod(**testmod_kwargs) -> doctest.TestResults:
    """
    Run doctests for the module, configured to ignore exception details and
    normalize whitespace.

    Accepts kwargs to pass to doctest.testmod().

    Add to modules to run doctests when run as a script:
    .. code-block:: text
        if __name__ == "__main__":
            from npc_io import testmod
            testmod()

    """
    _ = testmod_kwargs.setdefault(
        "optionflags",
        doctest.NORMALIZE_WHITESPACE
        | doctest.ELLIPSIS
        | doctest.IGNORE_EXCEPTION_DETAIL,
    )
    return doctest.testmod(**testmod_kwargs)


if __name__ == "__main__":
    testmod()
