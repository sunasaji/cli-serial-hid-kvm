"""Tests for CLI argument parsing."""

import pytest

from cli_serial_hid_kvm.cli import build_parser


@pytest.fixture
def parser():
    return build_parser()


class TestGlobalOptions:
    def test_host_option(self, parser):
        args = parser.parse_args(["-H", "10.0.0.1", "info"])
        assert args.host == "10.0.0.1"

    def test_port_option(self, parser):
        args = parser.parse_args(["-p", "1234", "info"])
        assert args.port == 1234

    def test_no_global_options(self, parser):
        args = parser.parse_args(["info"])
        assert args.host is None
        assert args.port is None


class TestTypeCommand:
    def test_basic(self, parser):
        args = parser.parse_args(["type", "hello"])
        assert args.command == "type"
        assert args.text == "hello"
        assert args.delay is None

    def test_with_delay(self, parser):
        args = parser.parse_args(["type", "hello", "-d", "50"])
        assert args.delay == 50


class TestKeyCommand:
    def test_basic(self, parser):
        args = parser.parse_args(["key", "enter"])
        assert args.key == "enter"
        assert args.mod is None

    def test_with_modifiers(self, parser):
        args = parser.parse_args(["key", "c", "-m", "ctrl"])
        assert args.mod == ["ctrl"]

    def test_multiple_modifiers(self, parser):
        args = parser.parse_args(["key", "a", "-m", "ctrl", "-m", "shift"])
        assert args.mod == ["ctrl", "shift"]


class TestKeysCommand:
    def test_basic(self, parser):
        args = parser.parse_args(["keys", '[{"key":"a"}]'])
        assert args.steps_json == '[{"key":"a"}]'

    def test_with_delay(self, parser):
        args = parser.parse_args(["keys", '[{"key":"a"}]', "-d", "200"])
        assert args.delay == 200


class TestMoveCommand:
    def test_absolute(self, parser):
        args = parser.parse_args(["move", "500", "300"])
        assert args.x == 500
        assert args.y == 300
        assert args.relative is False

    def test_relative(self, parser):
        args = parser.parse_args(["move", "10", "-5", "-r"])
        assert args.x == 10
        assert args.y == -5
        assert args.relative is True


class TestClickCommand:
    def test_defaults(self, parser):
        args = parser.parse_args(["click"])
        assert args.button == "left"
        assert args.x is None
        assert args.y is None

    def test_right_click_at_position(self, parser):
        args = parser.parse_args(["click", "-b", "right", "-x", "100", "-y", "200"])
        assert args.button == "right"
        assert args.x == 100
        assert args.y == 200


class TestDragCommand:
    def test_basic(self, parser):
        args = parser.parse_args(["drag", "100", "200", "500", "600"])
        assert args.start_x == 100
        assert args.start_y == 200
        assert args.end_x == 500
        assert args.end_y == 600
        assert args.button == "left"

    def test_with_button(self, parser):
        args = parser.parse_args(["drag", "0", "0", "10", "10", "-b", "right"])
        assert args.button == "right"


class TestScrollCommand:
    def test_positive(self, parser):
        args = parser.parse_args(["scroll", "5"])
        assert args.amount == 5

    def test_negative(self, parser):
        args = parser.parse_args(["scroll", "-5"])
        assert args.amount == -5


class TestCaptureCommand:
    def test_defaults(self, parser):
        args = parser.parse_args(["capture"])
        assert args.output is None
        assert args.base64 is False

    def test_with_output(self, parser):
        args = parser.parse_args(["capture", "-o", "test.jpg"])
        assert args.output == "test.jpg"

    def test_base64_flag(self, parser):
        args = parser.parse_args(["capture", "--base64"])
        assert args.base64 is True


class TestExecCommand:
    def test_basic(self, parser):
        args = parser.parse_args(["exec", "ls -la"])
        assert args.command == "ls -la"
        assert args.wait == 1.0

    def test_with_wait(self, parser):
        args = parser.parse_args(["exec", "make", "-w", "5"])
        assert args.wait == 5.0


class TestDeviceCommands:
    def test_set_device(self, parser):
        args = parser.parse_args(["set-device", "0"])
        assert args.device == "0"

    def test_set_resolution(self, parser):
        args = parser.parse_args(["set-resolution", "1920", "1080"])
        assert args.width == 1920
        assert args.height == 1080


class TestRequiredSubcommand:
    def test_no_subcommand_exits(self, parser):
        with pytest.raises(SystemExit):
            parser.parse_args([])
