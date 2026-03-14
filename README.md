# cli-serial-hid-kvm

CLI tool for KVM control — thin client for [serial-hid-kvm](https://github.com/sunasaji/serial-hid-kvm).

## Architecture

```
┌──────────┐       TCP        ┌─────────────────┐     USB/HDMI     ┌───────────┐
│  shkvm   │ ──────────────── │ serial-hid-kvm  │ ──────────────── │ Target PC │
│  (CLI)   │    port 9329     │   (server)      │   CH9329 + Cap   │           │
└──────────┘                  └─────────────────┘                  └───────────┘
```

The CLI connects to a running `serial-hid-kvm` server over TCP. The server handles all hardware interaction (USB HID via CH9329 and HDMI capture). OCR is performed locally by the CLI using Tesseract.

## Prerequisites

- **serial-hid-kvm** server running with `--headless --api` (or with GUI + API enabled)
- **Tesseract OCR** installed for `ocr` and `exec` commands
- **Python 3.10+**

## Installation

```bash
pip install cli-serial-hid-kvm
```

Or for development:

```bash
git clone https://github.com/sunasaji/cli-serial-hid-kvm.git
cd cli-serial-hid-kvm
pip install -e .
```

## Quick Start

```bash
# Start the KVM server (on the machine connected to target PC)
serial-hid-kvm --headless --api

# Use shkvm from any machine that can reach the server
shkvm info                          # check connection
shkvm type "ls -la{enter}"          # type on target PC
echo "ls -la{enter}" | shkvm type   # same, via stdin
shkvm capture -o screen.jpg         # take screenshot
shkvm ocr                           # read screen text
shkvm exec "echo hello" -w 2        # run command and read output
```

## Command Reference

### Keyboard

| Command | Description |
|---|---|
| `shkvm type [TEXT] [-d MS] [-r]` | Type text with optional char delay. Supports inline tags: `{enter}`, `{tab}`, `{ctrl+c}`, `{0xNN}`. Whitelist-based: unknown `{content}` passes through literally. `-r` (raw mode) disables tags, `\n` → Enter. Text can be passed via stdin instead of argument |
| `shkvm key KEY [-m MOD]` | Send single key press. `-m` can be repeated: `-m ctrl -m shift` |
| `shkvm keys [JSON] [-d MS]` | Send key sequence from JSON array. JSON can be passed via stdin instead of argument |

### Mouse

| Command | Description |
|---|---|
| `shkvm move X Y [-r]` | Move cursor (absolute, or relative with `-r`) |
| `shkvm click [-b BUTTON] [-x X] [-y Y]` | Click (default: left) |
| `shkvm drag X1 Y1 X2 Y2 [-b BUTTON]` | Drag from start to end |
| `shkvm scroll AMOUNT` | Scroll wheel (+up, -down) |

### Screen

| Command | Description |
|---|---|
| `shkvm capture [-o FILE] [--base64]` | Save screenshot or output base64 to stdout |
| `shkvm ocr` | Capture + OCR, print text to stdout |
| `shkvm exec CMD [-w SEC]` | Type command, Enter, wait, then OCR |

### Device Management

| Command | Description |
|---|---|
| `shkvm info` | Show device info (JSON) |
| `shkvm devices` | List capture devices |
| `shkvm set-device DEV` | Switch capture device by index or path |
| `shkvm set-resolution W H` | Set capture resolution |

### Stdin Support

`type` and `keys` accept input from stdin instead of a positional argument. If both are provided, the command exits with an error.

```bash
# Pass text via stdin
echo "hello world" | shkvm type
cat script.txt | shkvm type -r

# Pass JSON via stdin
echo '[{"key":"enter"}]' | shkvm keys
cat sequence.json | shkvm keys -d 200

# Error: both argument and stdin
echo "hello" | shkvm type "world"   # => Error
```

### Global Options

| Option | Description |
|---|---|
| `-H, --host HOST` | KVM server host (overrides `SHKVM_API_HOST`) |
| `-p, --port PORT` | KVM server port (overrides `SHKVM_API_PORT`) |

## Configuration

All settings can be configured via environment variables:

| Variable | Default | Description |
|---|---|---|
| `SHKVM_API_HOST` | `127.0.0.1` | KVM server host |
| `SHKVM_API_PORT` | `9329` | KVM server port |
| `SHKVM_OCR_CMD` | (auto-detect) | Path to Tesseract binary |
| `SHKVM_CAPTURE_LOG_DIR` | `~/.local/share/cli-serial-hid-kvm/captures` | Capture log directory (set to empty string to disable) |

## License

MIT
