"""CLI for KVM control — thin client that delegates to KVM server."""

import argparse
import base64
import datetime
import io
import json
import os
import sys
import time

from PIL import Image

from .config import config
from serial_hid_kvm.client import KvmClient, KvmClientError
from .ocr import TerminalOCR

_client: KvmClient | None = None
_ocr: TerminalOCR | None = None


def get_client() -> KvmClient:
    global _client
    if _client is None:
        _client = KvmClient(config.kvm_host, config.kvm_port)
        _client.connect()
    return _client


def get_ocr() -> TerminalOCR:
    global _ocr
    if _ocr is None:
        _ocr = TerminalOCR(config.tesseract_cmd)
    return _ocr


def _save_capture_log(image: Image.Image, suffix: str = "") -> str | None:
    """Save a capture image to the log directory if configured."""
    log_dir = config.capture_log_dir
    if log_dir is None:
        return None
    try:
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        tag = f"_{suffix}" if suffix else ""
        filename = f"{ts}{tag}.jpg"
        filepath = os.path.join(log_dir, filename)
        image.save(filepath, format="JPEG", quality=85)
        return filepath
    except Exception:
        return None


def _capture_image(quality: int = 85) -> Image.Image:
    """Fetch a frame from KVM server and return as PIL Image."""
    jpeg_bytes, w, h = get_client().capture_frame_jpeg(quality)
    return Image.open(io.BytesIO(jpeg_bytes))


def _error(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 1


# ── Subcommand handlers ──────────────────────────────────────────────


def _read_input(arg_value: str | None, label: str) -> str:
    """Return arg_value or stdin content; error if both or neither are given."""
    has_arg = arg_value is not None
    has_stdin = not sys.stdin.isatty()
    if has_arg and has_stdin:
        raise SystemExit(f"Error: {label} provided both as argument and via stdin")
    if not has_arg and not has_stdin:
        raise SystemExit(f"Error: {label} required as argument or via stdin")
    if has_arg:
        return arg_value
    return sys.stdin.read()


def cmd_type(args: argparse.Namespace) -> int:
    client = get_client()
    text = _read_input(args.text, "text")
    client.type_text(text, args.delay, raw=args.raw)
    print(f"Typed {len(text)} characters")
    return 0


def cmd_key(args: argparse.Namespace) -> int:
    client = get_client()
    modifiers = args.mod or []
    client.send_key(args.key, modifiers)
    mod_str = "+".join(modifiers) + "+" if modifiers else ""
    print(f"Sent: {mod_str}{args.key}")
    return 0


def cmd_keys(args: argparse.Namespace) -> int:
    client = get_client()
    steps_json = _read_input(args.steps_json, "steps_json")
    steps = json.loads(steps_json)
    default_delay = args.delay or 100
    client.send_key_sequence(steps, default_delay)
    print(f"Sent {len(steps)} key steps")
    return 0


def cmd_move(args: argparse.Namespace) -> int:
    client = get_client()
    client.mouse_move(args.x, args.y, args.relative)
    if args.relative:
        print(f"Moved mouse by ({args.x}, {args.y})")
    else:
        print(f"Moved mouse to ({args.x}, {args.y})")
    return 0


def cmd_click(args: argparse.Namespace) -> int:
    client = get_client()
    client.mouse_click(args.button, args.x, args.y)
    pos_str = f" at ({args.x}, {args.y})" if args.x is not None and args.y is not None else ""
    print(f"Clicked {args.button}{pos_str}")
    return 0


def cmd_drag(args: argparse.Namespace) -> int:
    client = get_client()
    client.mouse_down(args.button, args.start_x, args.start_y)
    time.sleep(0.05)
    client.mouse_move(args.end_x, args.end_y)
    time.sleep(0.05)
    client.mouse_up(args.button, args.end_x, args.end_y)
    print(f"Dragged {args.button} from ({args.start_x}, {args.start_y}) to ({args.end_x}, {args.end_y})")
    return 0


def cmd_scroll(args: argparse.Namespace) -> int:
    client = get_client()
    client.mouse_scroll(args.amount)
    direction = "up" if args.amount > 0 else "down"
    print(f"Scrolled {direction} by {abs(args.amount)}")
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    image = _capture_image()
    _save_capture_log(image, "capture")
    if args.base64:
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=85)
        print(base64.standard_b64encode(buf.getvalue()).decode("ascii"))
    else:
        if args.output:
            output = args.output
        else:
            ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output = f"{ts}_shkvm.jpg"
        image.save(output, format="JPEG", quality=85)
        print(f"Saved: {output} ({image.width}x{image.height})")
    return 0


def cmd_ocr(args: argparse.Namespace) -> int:
    image = _capture_image()
    _save_capture_log(image, "ocr")
    text = get_ocr().extract_text(image)
    print(text)
    return 0


def cmd_exec(args: argparse.Namespace) -> int:
    client = get_client()
    # Raw mode: no tag interpretation for command text
    client.type_text(args.command, raw=True)
    time.sleep(0.1)
    client.send_key("enter")
    time.sleep(args.wait)
    image = _capture_image()
    _save_capture_log(image, "exec")
    text = get_ocr().extract_text(image)
    print(text)
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    info = get_client().get_device_info()
    print(json.dumps(info, indent=2, ensure_ascii=False))
    return 0


def cmd_devices(args: argparse.Namespace) -> int:
    result = get_client().list_capture_devices()
    devices = result.get("devices", [])
    if not devices:
        print("No capture devices found.")
    else:
        print(json.dumps(devices, indent=2, ensure_ascii=False))
    return 0


def cmd_set_device(args: argparse.Namespace) -> int:
    result = get_client().set_capture_device(args.device)
    cap_info = result.get("info", {})
    print(f"Switched to device {args.device}: {cap_info.get('width')}x{cap_info.get('height')} ({cap_info.get('backend')})")
    return 0


def cmd_set_resolution(args: argparse.Namespace) -> int:
    result = get_client().set_capture_resolution(args.width, args.height)
    cap_info = result.get("info", {})
    print(f"Resolution set: {cap_info.get('width')}x{cap_info.get('height')} (requested {args.width}x{args.height})")
    return 0


# ── Parser ────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shkvm",
        description="CLI tool for KVM control via serial-hid-kvm server",
    )
    parser.add_argument("-H", "--host", help="KVM server host (env: SHKVM_API_HOST)")
    parser.add_argument("-p", "--port", type=int, help="KVM server port (env: SHKVM_API_PORT)")

    sub = parser.add_subparsers(dest="command", required=True)

    # type
    p = sub.add_parser("type", help="Type text with inline tags")
    p.add_argument("text", nargs="?", default=None, help='Text to type, e.g. "ls -la{enter}"')
    p.add_argument("-d", "--delay", type=int, default=None, help="Delay between chars (ms)")
    p.add_argument("-r", "--raw", action="store_true",
                   help="Disable tag interpretation; newlines become Enter")
    p.set_defaults(func=cmd_type)

    # key
    p = sub.add_parser("key", help="Send a single key press")
    p.add_argument("key", help="Key name (e.g. enter, tab, a, f1)")
    p.add_argument("-m", "--mod", action="append", help="Modifier key (ctrl, shift, alt, win)")
    p.set_defaults(func=cmd_key)

    # keys
    p = sub.add_parser("keys", help="Send a key sequence (JSON)")
    p.add_argument("steps_json", nargs="?", default=None, help='JSON array, e.g. \'[{"key":"a"},{"key":"b"}]\'')
    p.add_argument("-d", "--delay", type=int, default=None, help="Default delay between steps (ms)")
    p.set_defaults(func=cmd_keys)

    # move
    p = sub.add_parser("move", help="Move mouse cursor")
    p.add_argument("x", type=int, help="X coordinate")
    p.add_argument("y", type=int, help="Y coordinate")
    p.add_argument("-r", "--relative", action="store_true", help="Relative movement")
    p.set_defaults(func=cmd_move)

    # click
    p = sub.add_parser("click", help="Click mouse button")
    p.add_argument("-b", "--button", default="left", choices=["left", "right", "middle"])
    p.add_argument("-x", type=int, default=None, help="X coordinate")
    p.add_argument("-y", type=int, default=None, help="Y coordinate")
    p.set_defaults(func=cmd_click)

    # drag
    p = sub.add_parser("drag", help="Drag mouse from start to end")
    p.add_argument("start_x", type=int)
    p.add_argument("start_y", type=int)
    p.add_argument("end_x", type=int)
    p.add_argument("end_y", type=int)
    p.add_argument("-b", "--button", default="left", choices=["left", "right", "middle"])
    p.set_defaults(func=cmd_drag)

    # scroll
    p = sub.add_parser("scroll", help="Scroll mouse wheel")
    p.add_argument("amount", type=int, help="Scroll amount (+up, -down)")
    p.set_defaults(func=cmd_scroll)

    # capture
    p = sub.add_parser("capture", help="Capture screen to file or stdout")
    p.add_argument("-o", "--output", default=None, help="Output file (default: YYYY-MM-DD_HH-MM-SS_shkvm.jpg)")
    p.add_argument("-e", "--base64", action="store_true", help="Output base64-encoded JPEG to stdout")
    p.set_defaults(func=cmd_capture)

    # ocr
    p = sub.add_parser("ocr", help="Capture screen and extract text via OCR")
    p.set_defaults(func=cmd_ocr)

    # exec
    p = sub.add_parser("exec", help="Type command, press Enter, wait, then OCR")
    p.add_argument("command", help="Command to execute")
    p.add_argument("-w", "--wait", type=float, default=1.0, help="Wait seconds (default: 1.0)")
    p.set_defaults(func=cmd_exec)

    # info
    p = sub.add_parser("info", help="Show device info")
    p.set_defaults(func=cmd_info)

    # devices
    p = sub.add_parser("devices", help="List capture devices")
    p.set_defaults(func=cmd_devices)

    # set-device
    p = sub.add_parser("set-device", help="Switch capture device")
    p.add_argument("device", help="Device index or path")
    p.set_defaults(func=cmd_set_device)

    # set-resolution
    p = sub.add_parser("set-resolution", help="Set capture resolution")
    p.add_argument("width", type=int)
    p.add_argument("height", type=int)
    p.set_defaults(func=cmd_set_resolution)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Apply CLI overrides to config
    if args.host:
        config.kvm_host = args.host
    if args.port:
        config.kvm_port = args.port

    try:
        rc = args.func(args)
        sys.exit(rc)
    except KvmClientError as e:
        sys.exit(_error(f"KVM server error: {e}"))
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        sys.exit(_error(f"Error: {e}"))


if __name__ == "__main__":
    main()
