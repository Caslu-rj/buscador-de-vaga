import docx
import pypdf
from packaging.version import Version


def test_pypdf_dependency_version() -> None:
    assert hasattr(pypdf, "__version__")
    version = Version(pypdf.__version__)
    assert version >= Version("6.0.0")
    assert version < Version("7.0.0")


def test_python_docx_dependency_version() -> None:
    assert hasattr(docx, "__version__")
    version = Version(docx.__version__)
    assert version >= Version("1.1.0")
    assert version < Version("2.0.0")
