from pathlib import Path

from framed_assistant.conformance import run


def test_public_contract_fixtures() -> None:
    assert run(Path("contracts")) == 0
