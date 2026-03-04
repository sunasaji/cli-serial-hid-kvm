"""Tests for CLI subcommand handlers with mocked KvmClient."""

import io
import json
from unittest import mock

import pytest
from PIL import Image

from cli_serial_hid_kvm.cli import (
    build_parser,
    cmd_type,
    cmd_key,
    cmd_keys,
    cmd_move,
    cmd_click,
    cmd_drag,
    cmd_scroll,
    cmd_capture,
    cmd_ocr,
    cmd_exec,
    cmd_info,
    cmd_devices,
    cmd_set_device,
    cmd_set_resolution,
)


def _make_jpeg_bytes() -> bytes:
    """Create a minimal valid JPEG in memory."""
    img = Image.new("RGB", (64, 48), color="black")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def mock_client():
    client = mock.MagicMock()
    client.capture_frame_jpeg.return_value = (_make_jpeg_bytes(), 64, 48)
    return client


@pytest.fixture(autouse=True)
def patch_globals(mock_client):
    """Patch get_client/get_ocr/_save_capture_log so no real connections are made."""
    with (
        mock.patch("cli_serial_hid_kvm.cli.get_client", return_value=mock_client),
        mock.patch("cli_serial_hid_kvm.cli._save_capture_log", return_value=None),
        mock.patch("cli_serial_hid_kvm.cli._capture_image") as mock_cap,
    ):
        mock_cap.return_value = Image.new("RGB", (64, 48), color="black")
        yield


@pytest.fixture
def parser():
    return build_parser()


# ── Keyboard ──────────────────────────────────────────────────────────


class TestCmdType:
    def test_calls_type_text(self, parser, mock_client, capsys):
        args = parser.parse_args(["type", "hello"])
        rc = cmd_type(args)
        assert rc == 0
        mock_client.type_text.assert_called_once_with("hello", None)
        assert "5 characters" in capsys.readouterr().out

    def test_with_delay(self, parser, mock_client):
        args = parser.parse_args(["type", "hi", "-d", "50"])
        cmd_type(args)
        mock_client.type_text.assert_called_once_with("hi", 50)


class TestCmdKey:
    def test_simple_key(self, parser, mock_client, capsys):
        args = parser.parse_args(["key", "enter"])
        rc = cmd_key(args)
        assert rc == 0
        mock_client.send_key.assert_called_once_with("enter", [])
        assert "enter" in capsys.readouterr().out

    def test_with_modifier(self, parser, mock_client, capsys):
        args = parser.parse_args(["key", "c", "-m", "ctrl"])
        cmd_key(args)
        mock_client.send_key.assert_called_once_with("c", ["ctrl"])
        assert "ctrl+c" in capsys.readouterr().out


class TestCmdKeys:
    def test_sends_sequence(self, parser, mock_client, capsys):
        steps_json = '[{"key":"a"},{"key":"b"}]'
        args = parser.parse_args(["keys", steps_json])
        rc = cmd_keys(args)
        assert rc == 0
        mock_client.send_key_sequence.assert_called_once_with(
            [{"key": "a"}, {"key": "b"}], 100,
        )
        assert "2 key steps" in capsys.readouterr().out


# ── Mouse ─────────────────────────────────────────────────────────────


class TestCmdMove:
    def test_absolute(self, parser, mock_client, capsys):
        args = parser.parse_args(["move", "500", "300"])
        rc = cmd_move(args)
        assert rc == 0
        mock_client.mouse_move.assert_called_once_with(500, 300, False)
        assert "to (500, 300)" in capsys.readouterr().out

    def test_relative(self, parser, mock_client, capsys):
        args = parser.parse_args(["move", "10", "-5", "-r"])
        cmd_move(args)
        mock_client.mouse_move.assert_called_once_with(10, -5, True)
        assert "by (10, -5)" in capsys.readouterr().out


class TestCmdClick:
    def test_default_left(self, parser, mock_client, capsys):
        args = parser.parse_args(["click"])
        rc = cmd_click(args)
        assert rc == 0
        mock_client.mouse_click.assert_called_once_with("left", None, None)
        assert "left" in capsys.readouterr().out

    def test_right_at_position(self, parser, mock_client, capsys):
        args = parser.parse_args(["click", "-b", "right", "-x", "100", "-y", "200"])
        cmd_click(args)
        mock_client.mouse_click.assert_called_once_with("right", 100, 200)
        out = capsys.readouterr().out
        assert "right" in out
        assert "(100, 200)" in out


class TestCmdDrag:
    @mock.patch("cli_serial_hid_kvm.cli.time")
    def test_drag_sequence(self, mock_time, parser, mock_client, capsys):
        args = parser.parse_args(["drag", "10", "20", "50", "60"])
        rc = cmd_drag(args)
        assert rc == 0
        mock_client.mouse_down.assert_called_once_with("left", 10, 20)
        mock_client.mouse_move.assert_called_once_with(50, 60)
        mock_client.mouse_up.assert_called_once_with("left", 50, 60)
        assert "(10, 20)" in capsys.readouterr().out


class TestCmdScroll:
    def test_scroll_down(self, parser, mock_client, capsys):
        args = parser.parse_args(["scroll", "-5"])
        rc = cmd_scroll(args)
        assert rc == 0
        mock_client.mouse_scroll.assert_called_once_with(-5)
        assert "down" in capsys.readouterr().out

    def test_scroll_up(self, parser, mock_client, capsys):
        args = parser.parse_args(["scroll", "3"])
        cmd_scroll(args)
        mock_client.mouse_scroll.assert_called_once_with(3)
        assert "up" in capsys.readouterr().out


# ── Screen ────────────────────────────────────────────────────────────


class TestCmdCapture:
    def test_saves_file(self, parser, tmp_path, capsys):
        output = str(tmp_path / "test.jpg")
        args = parser.parse_args(["capture", "-o", output])
        rc = cmd_capture(args)
        assert rc == 0
        assert (tmp_path / "test.jpg").exists()
        assert "test.jpg" in capsys.readouterr().out

    def test_default_filename_has_timestamp(self, parser, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        args = parser.parse_args(["capture"])
        rc = cmd_capture(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "_shkvm.jpg" in out
        assert ".jpg" in out

    def test_base64_output(self, parser, capsys):
        import base64
        args = parser.parse_args(["capture", "--base64"])
        rc = cmd_capture(args)
        assert rc == 0
        out = capsys.readouterr().out.strip()
        # Should be valid base64 that decodes to JPEG
        data = base64.standard_b64decode(out)
        assert data[:2] == b"\xff\xd8"  # JPEG magic bytes


class TestCmdOcr:
    def test_prints_text(self, parser, capsys):
        with mock.patch("cli_serial_hid_kvm.cli.get_ocr") as mock_get_ocr:
            mock_get_ocr.return_value.extract_text.return_value = "hello world"
            args = parser.parse_args(["ocr"])
            rc = cmd_ocr(args)
            assert rc == 0
            assert "hello world" in capsys.readouterr().out


class TestCmdExec:
    @mock.patch("cli_serial_hid_kvm.cli.time")
    def test_types_and_ocrs(self, mock_time, parser, mock_client, capsys):
        with mock.patch("cli_serial_hid_kvm.cli.get_ocr") as mock_get_ocr:
            mock_get_ocr.return_value.extract_text.return_value = "output text"
            args = parser.parse_args(["exec", "ls -la", "-w", "2"])
            rc = cmd_exec(args)
            assert rc == 0
            mock_client.type_text.assert_called_once_with("ls -la")
            mock_client.send_key.assert_called_once_with("enter")
            assert "output text" in capsys.readouterr().out


# ── Device management ─────────────────────────────────────────────────


class TestCmdInfo:
    def test_prints_json(self, parser, mock_client, capsys):
        mock_client.get_device_info.return_value = {"serial": "ok", "capture": "ok"}
        args = parser.parse_args(["info"])
        rc = cmd_info(args)
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["serial"] == "ok"


class TestCmdDevices:
    def test_no_devices(self, parser, mock_client, capsys):
        mock_client.list_capture_devices.return_value = {"devices": []}
        args = parser.parse_args(["devices"])
        rc = cmd_devices(args)
        assert rc == 0
        assert "No capture devices" in capsys.readouterr().out

    def test_with_devices(self, parser, mock_client, capsys):
        mock_client.list_capture_devices.return_value = {
            "devices": [{"index": 0, "name": "USB Cam"}],
        }
        args = parser.parse_args(["devices"])
        cmd_devices(args)
        out = capsys.readouterr().out
        assert "USB Cam" in out


class TestCmdSetDevice:
    def test_switches(self, parser, mock_client, capsys):
        mock_client.set_capture_device.return_value = {
            "info": {"width": 1920, "height": 1080, "backend": "v4l2"},
        }
        args = parser.parse_args(["set-device", "0"])
        rc = cmd_set_device(args)
        assert rc == 0
        assert "1920x1080" in capsys.readouterr().out


class TestCmdSetResolution:
    def test_sets(self, parser, mock_client, capsys):
        mock_client.set_capture_resolution.return_value = {
            "info": {"width": 1280, "height": 720},
        }
        args = parser.parse_args(["set-resolution", "1280", "720"])
        rc = cmd_set_resolution(args)
        assert rc == 0
        assert "1280x720" in capsys.readouterr().out
