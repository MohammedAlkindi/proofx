import hashlib
import io
import zipfile

import pytest
from codebase.experiments import unpack


def archive(names):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as zipped:
        for name in names:
            zipped.writestr(name, b"content")
    return stream.getvalue()


@pytest.mark.parametrize("name", ["../escape", "folder/file", "C:escape", "folder\\file", ".."])
def test_archive_paths_rejected(tmp_path, name):
    data = archive([name])
    with pytest.raises(ValueError, match="flat"):
        unpack(data, hashlib.sha256(data).hexdigest(), tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_pin_and_no_overwrite(tmp_path):
    data = archive(["manifest.json"])
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="SHA-256"):
        unpack(data, "0" * 64, output)
    digest = hashlib.sha256(data).hexdigest()
    unpack(data, digest, output)
    assert (output / "manifest.json").read_bytes() == b"content"
    with pytest.raises(FileExistsError):
        unpack(data, digest, output)


def test_symlink_rejected(tmp_path):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as zipped:
        entry = zipfile.ZipInfo("link")
        entry.create_system = 3
        entry.external_attr = 0o120777 << 16
        zipped.writestr(entry, "target")
    data = stream.getvalue()
    with pytest.raises(ValueError, match="regular"):
        unpack(data, hashlib.sha256(data).hexdigest(), tmp_path / "output")
