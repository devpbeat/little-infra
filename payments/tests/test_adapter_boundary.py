"""Architecture fitness test: third-party gateway SDKs must stay confined.

Design §1 boundary rule: `import pagopar_sdk` (and any future e-signature
SDK such as `docusign_esign`) may appear in exactly one module. This test
greps the source tree so a future PR can't accidentally leak the SDK into
domain code, views, or tests.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SEARCH_DIRS = ["apps", "payments_core", "adapters", "tests", "config"]
FORBIDDEN_IMPORTS = {
    "pagopar_sdk": "adapters/pagopar/client.py",
    "docusign_esign": "adapters/docusign/client.py",
}


def _iter_python_files():
    for directory in SEARCH_DIRS:
        base = REPO_ROOT / directory
        if base.exists():
            yield from base.rglob("*.py")


def test_gateway_sdk_imports_confined_to_single_module():
    import_pattern = re.compile(r"^\s*(import|from)\s+(\S+)")
    hits: dict[str, list[str]] = {module: [] for module in FORBIDDEN_IMPORTS}

    for path in _iter_python_files():
        if "__pycache__" in path.parts:
            continue
        text = path.read_text()
        for line in text.splitlines():
            match = import_pattern.match(line)
            if not match:
                continue
            imported = match.group(2)
            for module in FORBIDDEN_IMPORTS:
                if imported == module or imported.startswith(f"{module}."):
                    hits[module].append(str(path.relative_to(REPO_ROOT)))

    for module, expected_owner in FORBIDDEN_IMPORTS.items():
        files = set(hits[module])
        if not files:
            # Not wired yet (e.g. docusign_esign) — nothing to enforce.
            continue
        assert files == {expected_owner}, (
            f"{module} must be imported only from {expected_owner}, found in: {sorted(files)}"
        )
