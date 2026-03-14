# shkvm — CLI Reference for LLM Agents

`shkvm` is a CLI tool for controlling a remote PC via [serial-hid-kvm](https://github.com/sunasaji/serial-hid-kvm).

## Commands

### Keyboard
```
shkvm type "ls -la{enter}"              # type text (supports {enter}, {tab}, {ctrl+c}, {0xNN})
shkvm type "hello" -d 50                # with 50ms char delay
echo "ls -la{enter}" | shkvm type       # text from stdin
shkvm key enter                         # single key press
shkvm key c -m ctrl                     # Ctrl+C
shkvm key f4 -m alt                     # Alt+F4
shkvm keys '[{"key":"a"},{"key":"b"}]'  # key sequence (JSON)
cat seq.json | shkvm keys               # JSON from stdin
```

### Mouse
```
shkvm move 500 300                      # move to absolute position
shkvm move 10 -5 -r                     # relative move
shkvm click                             # left click
shkvm click -b right                    # right click
shkvm click -b left -x 500 -y 300      # click at position
shkvm drag 100 200 500 600              # drag from (100,200) to (500,600)
shkvm scroll -5                         # scroll down 5 units
shkvm scroll 3                          # scroll up 3 units
```

### Screen
```
shkvm capture                           # save YYYY-MM-DD_HH-MM-SS_shkvm.jpg
shkvm capture -o path/to/file.jpg       # save to specific path
shkvm capture -e                        # output base64-encoded JPEG to stdout
shkvm ocr                               # capture + OCR → stdout
shkvm exec "ls -la"                     # type command, Enter, wait 1s, OCR
shkvm exec "make build" -w 5            # wait 5 seconds before OCR
```

### Device Management
```
shkvm info                              # show device info (JSON)
shkvm devices                           # list capture devices
shkvm set-device 0                      # switch capture device
shkvm set-resolution 1920 1080          # set capture resolution
```

## Global Options

```
shkvm -H 192.168.1.10 -p 9329 type "hello"   # specify host/port
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SHKVM_API_HOST` | `127.0.0.1` | KVM server host |
| `SHKVM_API_PORT` | `9329` | KVM server port |
| `SHKVM_OCR_CMD` | (auto) | Path to tesseract binary |
| `SHKVM_CAPTURE_LOG_DIR` | `~/.local/share/cli-serial-hid-kvm/captures` | Capture log dir (empty string to disable) |
