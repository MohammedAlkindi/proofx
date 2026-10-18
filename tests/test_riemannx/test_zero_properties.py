"""Tests for ReimannX ZeroProperties module (smoke tests)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))


class TestZeroPropertiesImport:
    def test_module_importable(self):
        """Ensure ZeroProperties module loads without errors."""
        import importlib

        mod = importlib.import_module("codebase.reimannx.zero_properties.zero_properties")
        assert mod is not None

    def test_backend_type_enum_exists(self):
        from codebase.reimannx.zero_properties.zero_properties import BackendType

        assert BackendType.CPU is not None
        assert BackendType.GPU is not None

    def test_precision_mode_enum_exists(self):
        from codebase.reimannx.zero_properties.zero_properties import PrecisionMode

        assert PrecisionMode.DOUBLE is not None

    def test_verification_method_enum_exists(self):
        from codebase.reimannx.zero_properties.zero_properties import VerificationMethod

        assert VerificationMethod.NUMERIC is not None
        assert VerificationMethod.SYMBOLIC is not None
        assert VerificationMethod.HYBRID is not None
