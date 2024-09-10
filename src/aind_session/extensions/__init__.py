# Explicitly re-export extension classes, so that staticmethods/classmethods are available to users via the package namespace
from aind_session.extensions.ecephys import Ecephys as ecephys

__all__ = ["ecephys"]
