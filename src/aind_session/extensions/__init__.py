# Explicitly re-export extension classes, so that staticmethods/classmethods are available to users via the package namespace
from aind_session.extensions.ecephys import EcephysExtension as ecephys
from aind_session.extensions.lims import LimsExtension as lims

__all__ = ["ecephys", "lims"]
