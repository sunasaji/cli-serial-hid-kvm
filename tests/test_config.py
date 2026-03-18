"""Tests for config module."""

import os
from unittest import mock


def _make_config():
    """Create a fresh Config instance (bypasses module-level singleton)."""
    from cli_serial_hid_kvm.config import Config
    return Config()


class TestConfigDefaults:
    def test_default_host(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = _make_config()
            assert cfg.kvm_host == "127.0.0.1"

    def test_default_port(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = _make_config()
            assert cfg.kvm_port == 9329

    def test_default_tesseract_cmd_is_none(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = _make_config()
            assert cfg.tesseract_cmd is None

    def test_default_capture_log_dir_exists(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = _make_config()
            assert cfg.capture_log_dir is not None
            assert "cli-serial-hid-kvm" in cfg.capture_log_dir
            assert cfg.capture_log_dir.endswith("captures")


class TestConfigEnvOverrides:
    def test_host_override(self):
        with mock.patch.dict(os.environ, {"SHKVM_API_HOST": "10.0.0.1"}):
            cfg = _make_config()
            assert cfg.kvm_host == "10.0.0.1"

    def test_port_override(self):
        with mock.patch.dict(os.environ, {"SHKVM_API_PORT": "1234"}):
            cfg = _make_config()
            assert cfg.kvm_port == 1234

    def test_tesseract_cmd_override(self):
        with mock.patch.dict(os.environ, {"SHKVM_OCR_CMD": "/usr/local/bin/tesseract"}):
            cfg = _make_config()
            assert cfg.tesseract_cmd == "/usr/local/bin/tesseract"

    def test_capture_log_dir_override(self):
        with mock.patch.dict(os.environ, {"SHKVM_CAPTURE_LOG_DIR": "/tmp/caps"}):
            cfg = _make_config()
            assert cfg.capture_log_dir == "/tmp/caps"

    def test_capture_log_dir_disabled(self):
        with mock.patch.dict(os.environ, {"SHKVM_CAPTURE_LOG_DIR": ""}):
            cfg = _make_config()
            assert cfg.capture_log_dir is None
