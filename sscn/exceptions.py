class FieldNotRegistered(Exception):
    """Raised when a page trys to return an 
    unregisterd field.
    """
    def __init__(self, field_name, cls):
        self.field_name = field_name
        self.cls = cls

    def __str__(self):
        return (
            f'`{self.cls.__name__}.fetch()` returned field'
            f"`{self.field_name}`, but it's not registered"
            'in the `fields` list of the Page class.'
        )

    def __repr__(self):
        return str(self)

class ContentUnavailable(Exception):
    """Base exception to raise whenever a
    registered field can not be returned.
    """

class ContentNotFound(ContentUnavailable):
    """Raised when a remote source does't
    contain the required field of a standard,
    or does't document the standard at all.
    """

class StandardNotFound(ContentNotFound):
    """Raised when a standard is not found in
    a origin."""

class RequestError(ContentUnavailable):
    """Raised when failed to request
    content from the remote source, typically
    due to network or authentication issues.
    """

    def __init__(self, e):
        self.error = e
