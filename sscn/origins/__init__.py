def iter_origin_cls(name):
    from .ccsn import CCSNOrigin
    from .bzorg import BZOrgOrigin
    from .csres import CSRESOrigin
    from .bzko import BzkoOrigin
    
    return (CCSNOrigin, BZOrgOrigin, CSRESOrigin, BzkoOrigin)