# Development

## Project Setup

The client is written in MicroPython (as of writing 1.24.1) for the ESP32.

LVGL (9.2) is our display engine for writing the LCD UI.

## Client Firmware

Instead of following the standard MicroPython instructions for flashing the bords, it needs a special build with the LVGL code and bindings to python including.

I am using the great project https://github.com/lvgl-micropython/lvgl_micropython, an unoffical fork which has made significant changes to improve deployability.

An original lengthy attempt was made to use the original project at https://github.com/lvgl/lv_micropython, but while I could eventually build for ESP_GENERIC_C3 and ESP_GENERIC_C6 from the `update/micropython_v1.24.1` branch, I still had issues importing the `lvgl` module from inside the firmware.

### Building

Python 3.8-3.12 are supported in lvgl_micropython, although patching `builder/esp32.py L1427` is possible for 3.13 in my testing so far.
If you're lucky, you can just run the following. This will install MicroPython, LVGL, Bindings and ESP-IDF as submodules and try to build a binary.

Board types are available at https://github.com/micropython/micropython/tree/master/ports/esp32/boards
The display types are available at https://github.com/lvgl-micropython/lvgl_micropython?tab=readme-ov-file#supported-display-ics

```
cd lvgl_micropython
python3 make.py esp32 BOARD=ESP32_GENERIC_C3 DISPLAY=GC9A01
```

On my board there is bug with the interaction between MicroPython 1.24.1, the ESP_GENERIC_C3 and ESP-IDF 5.2.3, you may need to add the following line to `lvgl_micropython/lib/micropython/ports/esp32/boards/ESP32_GENERIC_C3/mpconfigboard.h`:

```
#define USB_SERIAL_JTAG_PACKET_SZ_BYTES (64)
```

It will output a command to flash the file it made, something like this:

```
~/.espressif/python_env/idf5.2_py3.13_env/bin/python -m esptool --chip esp32c3 -b 460800 --before default_reset --after hard_reset write_flash --flash_mode dio --flash_size 4MB --flash_freq 80m --erase-all 0x0 ./build/lvgl_micropy_ESP32_GENERIC_C3-4.bin
```

With any luck with your ESP32 device in "boot" mode, this should erase and flash nicely!

### Loading

For quick tests you can load files inline in the REPL

You can use rshell from pip.

```
$ rshell -p /dev/tty.usbmodem5101 -b 115200 --editor nano

repl

CTRL-E

[paste code]

CTRL-D
```

To exit the repl: `Ctrl-A Ctrl-X`

#### Webrepl

I've had mixed success with `webrepl` once loading in all the networking code. The websocket appears to hang. The tutorial I followed was:
https://www.techcoil.com/blog/how-to-setup-micropython-webrepl-on-your-esp32-development-board/

### Developing

From the lvgl docs:

#### FAQ
> How can I know which LittlevGL objects and functions are available on Micropython?

- Run Micropython with LittlevGL module enabled (for example, lv_micropython)
- Open the REPL (interactive console)
- `import lvgl as lv`
- Type `lv.` + TAB for completion.
- All supported classes and functions of LittlevGL will be displayed.

More options
- `help(lv)`
- `print('\n'.join(dir(lv)))` You can also do that recursively. For example `lv.button`. + TAB, or `print('\n'.join(dir(lv.button)))`

## Server

The server is in the server directly. You can run this directly on your devlopment machine.
