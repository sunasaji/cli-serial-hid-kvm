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

## For LLM Agents

If you are an LLM agent, see [SHKVM.md](SHKVM.md) for a concise CLI reference including all commands, options, supported characters, and environment variables.

## Quick Start

```bash
# Start the KVM server (on the machine connected to target PC)
serial-hid-kvm --headless --api

# Use shkvm from any machine that can reach the server
shkvm info                          # check connection
printf 'ls -la\n' | shkvm type      # type on target PC (raw mode, \n becomes Enter)
shkvm capture -o screen.jpg         # take screenshot
shkvm ocr                           # read screen text
shkvm exec "echo hello" -w 2        # run command and read output
```

## Command Reference

### Keyboard

| Command | Description |
|---|---|
| `shkvm type [TEXT] [-f FILE] [-d MS] [-r\|-t]` | Type text with optional char delay. `-d` sets delay between each keystroke in milliseconds (default: 20ms). Supports inline tags: `{enter}`, `{tab}`, `{ctrl+c}`, `{0xNN}`. Whitelist-based: unknown `{content}` passes through literally. `-r` (raw mode) disables tags; actual line breaks in the input become Enter. `-f` reads from file (`-f -` for explicit stdin). Text arg defaults to tag mode; stdin/file default to raw mode. Use `-t` to enable tags for stdin/file |
| `shkvm key KEY [-m MOD]` | Send single key press. `-m` can be repeated: `-m ctrl -m shift` |
| `shkvm keys [JSON] [-d MS]` | Send key sequence from JSON array. `-d` sets default delay between steps in milliseconds (default: 100ms); each step can override with `delay_ms`. JSON can be passed via stdin instead of argument |

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

### Stdin and File Input

When the text argument is omitted, `type` reads from stdin line by line. Use `--file`/`-f` to read from a file, or `-f -` for explicit stdin.

Stdin and file input **default to raw mode** (no tag interpretation), since the typical use case is piping file/program output. Use `-t`/`--tags` to enable tag interpretation for these sources.

```bash
# Pipe from another command (raw by default; \n becomes Enter)
printf 'ls -la\n' | shkvm type

# Explicit stdin with "-f -"
cat commands.txt | shkvm type -f -

# Read from a file directly (raw by default)
shkvm type -f commands.txt

# File input with tag interpretation
shkvm type -f commands.txt -t

# Streaming (line-by-line as data arrives)
tail -f commands.fifo | shkvm type
```

If both a text argument and stdin are present, the text argument wins (stdin is ignored).

`-r`/`--raw` and `-t`/`--tags` are mutually exclusive.

`keys` also accepts input from stdin. If both argument and stdin are present, the argument wins.

```bash
# Pass JSON via stdin
echo '[{"key":"enter"}]' | shkvm keys
cat sequence.json | shkvm keys -d 200
```

### Supported Characters

HID keyboard input supports ASCII printable characters (`a-z`, `A-Z`, `0-9`, symbols, space), tab, and newline. Characters outside this set (Unicode, CJK, accented characters, control characters, etc.) cause an error.

In **tag mode** (default for text arg), special keys can be embedded as `{enter}`, `{tab}`, `{ctrl+c}`, `{0xNN}`, etc.

Available tags:

| Category | Tags |
|---|---|
| Enter / Space | `enter`, `return`, `space` |
| Navigation | `up`, `down`, `left`, `right`, `home`, `end`, `pageup`, `pagedown` |
| Editing | `backspace`, `delete`, `insert`, `tab` |
| Escape / Cancel | `escape`, `esc` |
| Function keys | `f1` – `f12` |
| Lock keys | `capslock`, `numlock`, `scrolllock` |
| System | `printscreen`, `pause` |
| Modifiers | `ctrl`, `shift`, `alt`, `win`, `gui`, `super`, `meta` |
| Left/right modifiers | `lctrl`, `rctrl`, `lshift`, `rshift`, `lalt`, `ralt`, `lwin`, `rwin` |
| Raw HID keycode | `0x00` – `0xFF` |

Modifiers are combined with `+`: `{ctrl+c}`, `{ctrl+shift+del}`, `{shift+0x87}`. `{0xNN}` allows sending any HID keycode by its hex value, which is useful for keys that have no named tag — for example, `{0x87}` sends the JIS `ろ` key (International1, HID 0x87). In **raw mode** (default for stdin/file), actual line break bytes in the input (LF 0x0A, CRLF 0x0D 0x0A, CR 0x0D) are sent as Enter and actual tab bytes (0x09) as Tab, with no tag interpretation. Two-character sequences like `\` `n` are not interpreted as control characters and are typed literally.

If the target PC uses a non-US keyboard layout, configure `--target-layout` on the KVM server (e.g. `jp106`, `uk105`, `de105`, `fr105`).

**Base64 workaround** for unsupported characters or binary data — encode on the host, decode on the target:

```bash
# Transfer text containing Unicode
echo "こんにちは世界" | base64 | shkvm type
shkvm exec "base64 -d <<< $(echo 'こんにちは世界' | base64)" -w 2

# Transfer a file via base64
base64 < file.bin | shkvm type
# Then on target: paste into `base64 -d > file.bin` and Ctrl+D
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

[MIT](LICENSE)
