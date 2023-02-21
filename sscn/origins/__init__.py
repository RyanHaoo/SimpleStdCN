def iter_origin_cls():
    """Return the origins tuple to be searched through."""
    # old circular dependence
    from .ccsn import CCSNOrigin
    from .bzorg import BZOrgOrigin
    from .csres import CSRESOrigin
    from .bzko import BzkoOrigin

    return (CCSNOrigin, BZOrgOrigin, CSRESOrigin, BzkoOrigin)
