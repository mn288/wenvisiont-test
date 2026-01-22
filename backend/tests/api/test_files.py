from unittest.mock import MagicMock, mock_open, patch

import pytest
from expects import equal, expect
from httpx import AsyncClient


@pytest.fixture
def mock_workspace_root():
    root = "/tmp/mock_workspace"
    with patch("api.v1.endpoints.files.WORKSPACE_ROOT", new=root):
        yield root


@pytest.mark.asyncio
async def test_list_files_success(client: AsyncClient, mock_workspace_root):
    # Mock os.path.exists (root and full_path)
    # Mock os.scandir
    with patch("os.path.exists", return_value=True), patch("os.scandir") as mock_scandir:
        # Setup scandir iterator
        entry1 = MagicMock()
        entry1.name = "file1.txt"
        entry1.is_dir.return_value = False
        entry1.is_file.return_value = True
        entry1.stat.return_value.st_size = 100

        entry2 = MagicMock()
        entry2.name = "dir1"
        entry2.is_dir.return_value = True
        entry2.is_file.return_value = False

        # scandir returns a context manager that yields the iterator
        mock_scandir.return_value.__enter__.return_value = [entry1, entry2]

        response = await client.get("/files/list?path=.")
        expect(response.status_code).to(equal(200))
        data = response.json()
        expect(len(data)).to(equal(2))
        # Sorting: Dirs first
        expect(data[0]["name"]).to(equal("dir1"))
        expect(data[0]["type"]).to(equal("directory"))
        expect(data[1]["name"]).to(equal("file1.txt"))
        expect(data[1]["type"]).to(equal("file"))


@pytest.mark.asyncio
async def test_list_files_invalid_path(client: AsyncClient, mock_workspace_root):
    response = await client.get("/files/list?path=../secret")
    expect(response.status_code).to(equal(400))


@pytest.mark.asyncio
async def test_list_files_not_found(client: AsyncClient, mock_workspace_root):
    with patch("os.path.exists", return_value=False):
        response = await client.get("/files/list?path=missing")
        expect(response.status_code).to(equal(404))


@pytest.mark.asyncio
async def test_list_files_error(client: AsyncClient, mock_workspace_root):
    with patch("os.path.exists", return_value=True), patch("os.scandir", side_effect=Exception("Disk error")):
        response = await client.get("/files/list?path=.")
        expect(response.status_code).to(equal(500))


@pytest.mark.asyncio
async def test_read_file_success(client: AsyncClient, mock_workspace_root):
    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.isfile", return_value=True),
        patch("builtins.open", mock_open(read_data="content")),
    ):
        response = await client.post("/files/read", json={"path": "test.txt"})
        expect(response.status_code).to(equal(200))
        expect(response.json()["content"]).to(equal("content"))


@pytest.mark.asyncio
async def test_read_file_invalid_path(client: AsyncClient, mock_workspace_root):
    response = await client.post("/files/read", json={"path": "../secret"})
    expect(response.status_code).to(equal(400))


@pytest.mark.asyncio
async def test_read_file_not_found(client: AsyncClient, mock_workspace_root):
    with patch("os.path.exists", return_value=False):
        response = await client.post("/files/read", json={"path": "missing.txt"})
        expect(response.status_code).to(equal(404))

    # Exist but not file
    with patch("os.path.exists", return_value=True), patch("os.path.isfile", return_value=False):
        response = await client.post("/files/read", json={"path": "folder"})
        expect(response.status_code).to(equal(404))


@pytest.mark.asyncio
async def test_read_file_binary(client: AsyncClient, mock_workspace_root):
    err = UnicodeDecodeError("utf-8", b"", 0, 1, "fail")
    m = mock_open()
    m.side_effect = err
    # mock_open raises when called? No, when .read() is called usually, or __enter__?
    # Context manager: with open(...) as f.
    # If open(...) raises, it's failed open.
    # UnicodeDecodeError happens during read usually if mode is 'r'.

    # Let's use simpler approach: mock read() to raise
    m_open = mock_open()
    # mocking the file handle read method
    m_open.return_value.read.side_effect = err

    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.isfile", return_value=True),
        patch("builtins.open", m_open),
    ):
        response = await client.post("/files/read", json={"path": "bin.dat"})
        expect(response.status_code).to(equal(200))  # It captures error and returns placeholder
        expect(response.json()["content"]).to(equal("[Binary File]"))


@pytest.mark.asyncio
async def test_read_file_error(client: AsyncClient, mock_workspace_root):
    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.isfile", return_value=True),
        patch("builtins.open", side_effect=Exception("Read Fail")),
    ):
        response = await client.post("/files/read", json={"path": "fail.txt"})
        expect(response.status_code).to(equal(500))
