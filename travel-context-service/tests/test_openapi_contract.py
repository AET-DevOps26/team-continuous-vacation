from pathlib import Path

import yaml

from app.main import app


def test_checked_in_openapi_operation_refs_match_fastapi():
    spec_path = (
        Path(__file__).resolve().parents[2]
        / "api-specification/travel-context.yaml"
    )
    checked_in = yaml.safe_load(spec_path.read_text())
    generated = app.openapi()

    for path, path_item in checked_in["paths"].items():
        assert path in generated["paths"]
        for method, operation in path_item.items():
            runtime_operation = generated["paths"][path][method]
            expected_request = operation["requestBody"]["content"]["application/json"][
                "schema"
            ]["$ref"]
            actual_request = runtime_operation["requestBody"]["content"][
                "application/json"
            ]["schema"]["$ref"]
            assert actual_request == expected_request

            expected_response = operation["responses"]["200"]["content"][
                "application/json"
            ]["schema"]["$ref"]
            actual_response = runtime_operation["responses"]["200"]["content"][
                "application/json"
            ]["schema"]["$ref"]
            assert actual_response == expected_response
