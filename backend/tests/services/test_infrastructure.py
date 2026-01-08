import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from expects import be, be_false, be_true, contain, equal, expect, have_keys

from models.infrastructure import S3Config
from services.infrastructure import InfrastructureService


@pytest.fixture
def mock_fs():
    with (
        patch("services.infrastructure.os") as MockOS,
        patch("services.infrastructure.shutil") as MockShutil,
        patch("services.infrastructure.open", new_callable=MagicMock) as MockOpen,
    ):  # open is built-in
        MockOS.path.join.side_effect = os.path.join
        MockOS.path.abspath.side_effect = os.path.abspath
        MockOS.path.relpath.side_effect = os.path.relpath
        # Fix: Ensure getenv returns None by default so it's not a Mock object (truthy)
        MockOS.getenv.return_value = None

        yield MockOS, MockShutil, MockOpen


@pytest.fixture
def mock_aioboto3():
    with patch("services.infrastructure.aioboto3") as MockAio:
        yield MockAio


def test_get_or_create_infrastructure_local(mock_fs):
    MockOS, _, _ = mock_fs
    service = InfrastructureService()

    # Mock exists=False to trigger makedirs
    MockOS.path.exists.return_value = False

    infra = service.get_or_create_infrastructure("t1")

    expect(infra.local_workspace_path).to(contain("/tmp/sfeir/workspace/t1"))
    expect(MockOS.makedirs.called).to(be_true)
    expect(infra.s3_config).to(be(None))


def test_cleanup(mock_fs):
    MockOS, MockShutil, _ = mock_fs
    service = InfrastructureService()

    MockOS.path.exists.return_value = True
    service.cleanup("t1")
    expect(MockShutil.rmtree.called).to(be_true)


def test_save_config(mock_fs):
    MockOS, _, MockOpen = mock_fs
    service = InfrastructureService()

    s3_conf = S3Config(bucket_name="b", region_name="r", access_key_id="k", secret_access_key="s")

    mock_file = MagicMock()
    MockOpen.return_value.__enter__.return_value = mock_file

    service.save_config(s3_conf)

    expect(MockOpen.call_args[0][0]).to(contain("infra_config.json"))
    # Verify json dump wrote something
    # json.dump writes to file.write
    expect(mock_file.write.called).to(be_true)


def test_list_files(mock_fs):
    MockOS, _, _ = mock_fs
    service = InfrastructureService()

    MockOS.path.exists.return_value = True
    # Walk yields (root, dirs, files)
    MockOS.walk.return_value = [("/tmp/ws/t1", [], ["f1.txt"])]

    files = service.list_files("t1")

    expect(len(files)).to(equal(1))
    expect(files[0]).to(have_keys("path", "name", "type"))
    expect(files[0]["name"]).to(equal("f1.txt"))


def test_read_file_success(mock_fs):
    MockOS, _, MockOpen = mock_fs
    service = InfrastructureService()

    # Mock validation
    MockOS.path.abspath.return_value = "/tmp/sfeir/workspace/t1/f1.txt"
    MockOS.path.exists.return_value = True

    mock_file = MagicMock()
    mock_file.read.return_value = "Content"
    MockOpen.return_value.__enter__.return_value = mock_file

    content = service.read_file("t1", "f1.txt")

    expect(content).to(equal("Content"))


def test_read_file_access_denied(mock_fs):
    MockOS, _, _ = mock_fs
    service = InfrastructureService()

    # Path traversal attack simulation
    MockOS.path.abspath.return_value = "/etc/passwd"

    # We must ensure workspace path is resolved correctly to compare
    # Mocking os.path.abspath(workspace) -> /tmp/sfeir/workspace/t1
    # Mocking os.path.abspath(target) -> /etc/passwd
    # Logic: if not target.startswith(workspace)...

    # We need side_effect to distinguish calls
    # We need side_effect to distinguish calls
    def abspath_side_effect(path):
        # Resolve '..' but keep it fake
        # If the path contains 'passwd', we simulate it resolving to /etc/passwd
        # causing the startswith check to fail.
        if "passwd" in path:
            return "/etc/passwd"
        return "/tmp/sfeir/workspace/t1"

    MockOS.path.abspath.side_effect = abspath_side_effect

    with pytest.raises(ValueError) as exc:
        service.read_file("t1", "../../../etc/passwd")

    expect(str(exc.value)).to(contain("Access Denied"))


@pytest.mark.asyncio
async def test_verify_s3_connection_success(mock_aioboto3):
    service = InfrastructureService()
    config = S3Config(bucket_name="b", region_name="r", access_key_id="k", secret_access_key="s")

    # Mock session client
    mock_session = mock_aioboto3.Session.return_value
    mock_client = AsyncMock()
    mock_session.client.return_value.__aenter__.return_value = mock_client

    result = await service.verify_s3_connection(config)

    expect(result).to(be_true)
    expect(mock_client.head_bucket.called).to(be_true)


@pytest.mark.asyncio
async def test_verify_s3_connection_fail(mock_aioboto3):
    service = InfrastructureService()
    config = S3Config(bucket_name="b", region_name="r", access_key_id="k", secret_access_key="s")

    mock_session = mock_aioboto3.Session.return_value
    mock_client = AsyncMock()
    mock_session.client.return_value.__aenter__.return_value = mock_client

    # Simulate error
    mock_client.head_bucket.side_effect = Exception("AWS Error")

    result = await service.verify_s3_connection(config)

    expect(result).to(be_false)


def test_get_or_create_infrastructure_env_s3(mock_fs):
    MockOS, _, _ = mock_fs
    service = InfrastructureService()

    # Mock env vars
    # Mock env vars via our MockOS.getenv side effect
    def getenv_side_effect(key, default=None):
        env = {"TEST_S3_BUCKET": "env-bucket", "TEST_S3_ACCESS_KEY": "k"}
        return env.get(key, default)

    MockOS.getenv.side_effect = getenv_side_effect

    infra = service.get_or_create_infrastructure("t1")
    expect(infra.s3_config).not_to(be(None))
    expect(infra.s3_config.bucket_name).to(equal("env-bucket"))


def test_save_config_create_base_workspace(mock_fs):
    MockOS, _, MockOpen = mock_fs
    service = InfrastructureService()

    # Case: Base workspace does not exist
    def exists_side_effect(path):
        return False

    MockOS.path.exists.side_effect = exists_side_effect

    mock_file = MagicMock()
    MockOpen.return_value.__enter__.return_value = mock_file

    service.save_config(None)

    expect(MockOS.makedirs.called).to(be_true)


def test_list_files_workspace_missing(mock_fs):
    MockOS, _, _ = mock_fs
    service = InfrastructureService()

    # Case: Workspace does not exist
    MockOS.path.exists.return_value = False

    files = service.list_files("t1")
    expect(files).to(equal([]))


def test_read_file_not_found(mock_fs):
    MockOS, _, _ = mock_fs
    service = InfrastructureService()

    # Valid path in workspace, but file missing
    # We must ensure abspath resolves correctly to pass validation
    MockOS.path.abspath.return_value = "/tmp/sfeir/workspace/t1/missing.txt"

    # Validation logic:
    # target = os.path.abspath(...) -> /tmp/sfeir/workspace/t1/missing.txt (mocked above)
    # workspace = ...
    # if not target.startswith(...) -> passed
    # if not os.path.exists(target) -> failed

    # We simulate exists returning False for the target
    MockOS.path.exists.return_value = False

    with pytest.raises(FileNotFoundError) as exc:
        service.read_file("t1", "missing.txt")

    expect(str(exc.value)).to(contain("File not found"))


@pytest.mark.asyncio
async def test_verify_s3_connection_list_buckets(mock_aioboto3):
    service = InfrastructureService()
    # Empty bucket name trigger list_buckets
    config = S3Config(bucket_name="", region_name="r", access_key_id="k", secret_access_key="s")

    mock_session = mock_aioboto3.Session.return_value
    mock_client = AsyncMock()
    mock_session.client.return_value.__aenter__.return_value = mock_client

    result = await service.verify_s3_connection(config)

    expect(result).to(be_true)
    expect(mock_client.list_buckets.called).to(be_true)
