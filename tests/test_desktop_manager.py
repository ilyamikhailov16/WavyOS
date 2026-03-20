import json
import pytest
from scripts.desktop_manager import DesktopManager, OperationStatus


@pytest.fixture
def manager(tmp_path):
    return DesktopManager(desktop_path=tmp_path)


def test_create_folder(manager, tmp_path):
    res = manager.create_folder("test_folder")
    assert res.status == OperationStatus.SUCCESS
    assert (tmp_path / "test_folder").is_dir()


def test_create_folder_outside_desktop(manager):
    res = manager.create_folder("../outside")
    assert res.status == OperationStatus.ERROR
    assert "Path" in res.message


def test_create_file(manager, tmp_path):
    res = manager.create_file("test.txt", content="hello")
    assert res.status == OperationStatus.SUCCESS
    assert (tmp_path / "test.txt").read_text(encoding="utf-8") == "hello"


def test_create_file_exists_no_overwrite(manager, tmp_path):
    (tmp_path / "test.txt").write_text("old", encoding="utf-8")
    res = manager.create_file("test.txt", content="new")
    assert res.status == OperationStatus.ERROR
    assert "already exists" in res.message
    assert (tmp_path / "test.txt").read_text(encoding="utf-8") == "old"


def test_create_file_in_subfolder(manager, tmp_path):
    res = manager.create_file("test.txt", content="sub", folder="sub_dir")
    assert res.status == OperationStatus.SUCCESS
    assert (tmp_path / "sub_dir" / "test.txt").read_text(encoding="utf-8") == "sub"


def test_create_json_file(manager, tmp_path):
    data = {"key": "value"}
    res = manager.create_json_file("data.json", data=data)
    assert res.status == OperationStatus.SUCCESS
    assert json.loads((tmp_path / "data.json").read_text(encoding="utf-8")) == data


def test_read_file(manager, tmp_path):
    (tmp_path / "read.txt").write_text("content", encoding="utf-8")
    res = manager.read_file("read.txt")
    assert res.status == OperationStatus.SUCCESS
    assert res.data["content"] == "content"


def test_read_file_not_found(manager):
    res = manager.read_file("missing.txt")
    assert res.status == OperationStatus.ERROR
    assert "not found" in res.message


def test_delete_file(manager, tmp_path):
    target = tmp_path / "to_delete.txt"
    target.touch()
    res = manager.delete("to_delete.txt")
    assert res.status == OperationStatus.SUCCESS
    assert not target.exists()


def test_delete_folder(manager, tmp_path):
    target = tmp_path / "to_delete_dir"
    target.mkdir()
    (target / "file.txt").touch()
    res = manager.delete("to_delete_dir")
    assert res.status == OperationStatus.SUCCESS
    assert not target.exists()


def test_rename(manager, tmp_path):
    src = tmp_path / "old.txt"
    src.write_text("test", encoding="utf-8")
    res = manager.rename("old.txt", "new.txt")
    assert res.status == OperationStatus.SUCCESS
    assert not src.exists()
    assert (tmp_path / "new.txt").read_text(encoding="utf-8") == "test"


def test_list_items(manager, tmp_path):
    (tmp_path / "file1.txt").touch()
    (tmp_path / "file2.txt").touch()
    (tmp_path / "dir1").mkdir()
    (tmp_path / ".hidden").touch()

    res = manager.list_items()
    assert res.status == OperationStatus.SUCCESS
    names = [item["name"] for item in res.data["items"]]
    assert "file1.txt" in names
    assert "file2.txt" in names
    assert "dir1" in names
    assert ".hidden" not in names


def test_get_info(manager):
    res = manager.get_info()
    assert res.status == OperationStatus.SUCCESS
    assert "desktop_path" in res.data
    assert "python_version" in res.data
