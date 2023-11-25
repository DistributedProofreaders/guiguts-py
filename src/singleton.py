"""Support for singleton classes

Supports class instantiation with zero args or variable args/kwargs

Usage:
    import singleton from singleton
    ...
    @singleton
    class MyClass():
        ...
"""


def singleton(cls):
    """Singleton decorator based on https://peps.python.org/pep-0318/#examples
    but with optional args/kwargs
    """

    instances = {}

    def getinstance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return getinstance
