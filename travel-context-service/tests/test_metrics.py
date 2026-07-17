import httpx
import pytest
from pydantic import BaseModel, ValidationError

from app.metrics import provider_failure_reason


class RequiredValue(BaseModel):
    value: int


def status_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://provider.example")
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError("provider failure", request=request, response=response)


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (httpx.ReadTimeout("slow provider"), "timeout"),
        (status_error(429), "rate_limit"),
        (status_error(400), "permanent"),
        (status_error(503), "upstream"),
        (httpx.ConnectError("unreachable"), "network"),
        (ValueError("invalid JSON"), "validation"),
        (RuntimeError("bug"), "unexpected"),
    ],
)
def test_provider_failure_reason_is_stable(error, reason):
    assert provider_failure_reason(error) == reason


def test_provider_failure_reason_classifies_schema_validation():
    with pytest.raises(ValidationError) as raised:
        RequiredValue.model_validate({})

    assert provider_failure_reason(raised.value) == "validation"
