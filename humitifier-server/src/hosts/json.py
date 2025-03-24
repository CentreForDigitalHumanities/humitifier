import json
from enum import Enum

from django.core.serializers.json import DjangoJSONEncoder


class HostJSONEncoder(DjangoJSONEncoder):
    """
    Encodes Python objects into JSON format, with extended support for
    Enum objects.

    This class provides a custom JSON encoding by extending the default
    behavior of DjangoJSONEncoder to convert Enum objects to their
    respective values. It supports Python objects consistent with
    DjangoJSONEncoder, while adding special handling for the Enum type.
    """

    def default(self, o):
        if isinstance(o, Enum):
            return o.value
        else:
            return super().default(o)

class HostJSONDecoder(json.JSONDecoder):
    # Stub for now, for easy expansion later
    pass
