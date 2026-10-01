from datetime import datetime
from typing import Annotated

from pydantic import PlainSerializer


def z(value):
    if value is None:
        return None
    return value.isoformat() + "Z"


UtcDateTime = Annotated[datetime, PlainSerializer(z, return_type=str, when_used="json")]
OptUtcDateTime = Annotated[datetime | None, PlainSerializer(z, return_type=str | None, when_used="json")]
