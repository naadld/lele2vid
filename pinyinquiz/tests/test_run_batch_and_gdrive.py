import os
import pytest
from unittest.mock import patch, MagicMock
from src.gdrive_uploader import TARGET_FOLDER_ID, GDriveUploader
from scripts.run_batch import TARGET_GDRIVE_FOLDER_ID, trigger_product_qc

def test_default_target_gdrive_folder_id():
    assert TARGET_FOLDER_ID == "1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB"
    assert TARGET_GDRIVE_FOLDER_ID == "1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB"

def test_gdrive_uploader_init_default_and_env(monkeypatch):
    monkeypatch.delenv("GDRIVE_TARGET_FOLDER", raising=False)
    monkeypatch.delenv("GDRIVE_FOLDER_ID", raising=False)

    with patch.object(GDriveUploader, "_authenticate", return_value=None):
        uploader = GDriveUploader()
        assert uploader.folder_id == "1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB"

        # Explicit override
        uploader2 = GDriveUploader(folder_id="CUSTOM_FOLDER_123")
        assert uploader2.folder_id == "CUSTOM_FOLDER_123"

        # Env override
        monkeypatch.setenv("GDRIVE_TARGET_FOLDER", "ENV_FOLDER_456")
        uploader3 = GDriveUploader()
        assert uploader3.folder_id == "ENV_FOLDER_456"

@patch("scripts.run_qc.run_auto_qc")
def test_trigger_product_qc_local(mock_run_qc):
    mock_run_qc.return_value = None
    res = trigger_product_qc(row_id="15")
    assert res is True
    mock_run_qc.assert_called_once_with(target_row_id="15")

@patch("subprocess.run")
def test_trigger_product_qc_github_actions(mock_subproc, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    mock_subproc.return_value = MagicMock(returncode=0, stderr="")
    
    res = trigger_product_qc(row_id="22")
    assert res is True
    mock_subproc.assert_called_once()
