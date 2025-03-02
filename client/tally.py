#!/usr/bin/env python
"""
TallyHo Client for ESP32 MicroPython with LVGL
"""
import lcd_bus

# from lvgl_micropython import display_driver_framework
from micropython import const
import machine
import time
import errno
from machine import WDT

_LCD_BYTE_ORDER_RGB = const(0x00)
_LCD_BYTE_ORDER_BGR = const(0x08)

COLOR_WARNING = 0xFF6600
COLOR_OK = 0x007700

COLOR_LIVE = 0xFF0000
COLOR_PREV = COLOR_OK
COLOR_STDBY = 0x222222

CAMERA_NUMBER: int = -1
CAM_LIVE: int = 0
CAM_PREV: int = 0

LED_COLOR_RED = [255, 0, 0]
LED_COLOR_GREEN = [0, 255, 0]
LED_COLOR_BLUE = [0, 0, 255]
LED_COLOR_YELLOW = [255, 255, 0]
LED_COLOR_PURPLE = [255, 0, 255]
LED_COLOR_CYAN = [0, 255, 255]
LED_COLOR_WHITE = [255, 255, 255]
LED_COLOR_OFF = [0, 0, 0]
LED_COLORS = [
    LED_COLOR_RED,
    LED_COLOR_YELLOW,
    LED_COLOR_GREEN,
    LED_COLOR_CYAN,
    LED_COLOR_BLUE,
    LED_COLOR_PURPLE,
    LED_COLOR_OFF,
]

MAX_CAMERAS = 99

PING_PERIOD_MS = 1000 * 10  # 10 secs
wdt: WDT

# LVGL display engine
import lvgl as lv

# The main lvgl Tally Screen
scrn: lv.obj = None

# MODEL = "ESP32-2424S012"
MODEL = "ESP32-C6-LCD-1.47"

# Board config defaults

_CPU_FREQ_HZ = 160000000  # 160Mhz. Valid options 80, 160 for C series ESP32
_MISO = -1  # Uses bidirection MOSI line instead
_HOST = 1  # SPI2, SPI1 is dedicated on ESP32 to flash
_TOUCH_CS = -1  # No touch
_TOUCH_FREQ = 10000000
_LCD_FREQ = 80000000
_LCD_ROTATION = lv.DISPLAY_ROTATION._0
_LCD_BYTE_ORDER = _LCD_BYTE_ORDER_BGR
_LCD_BYTE_COLOR_SWAP = True
_LCD_OFFSET_X = 0
_LCD_OFFSET_Y = 0
_NEOPIXEL = -1
_NEOPIXEL_COUNT = 1
_NEOPIXEL_BYTE_ORDER = (
    0,
    1,
    2,
)  # R, B, G as array indexes, e.g. R is position 0 in the color array, G is position 1 etc

# Sadly we don't have match case in this version of MicroPython.
if MODEL == "ESP32-2424S012":
    _WIDTH = 240
    _HEIGHT = 240
    _BL = 3
    _DC = 2
    _MOSI = 7
    _MISO = -1
    _SCK = 6
    _LCD_CS = 10
    _LCD_DRIVER_TYPE = "GC9A01"

    _TOUCH_CS = 18


elif MODEL == "ESP32-C6-LCD-1.47":
    _WIDTH = 172
    _HEIGHT = 320
    _BL = 22
    _DC = 15
    _MOSI = 6
    _SCK = 7

    _LCD_CS = 14
    _LCD_DRIVER_TYPE = "ST7789"
    _LCD_ROTATION = lv.DISPLAY_ROTATION._270  # USB C port on left
    _LCD_OFFSET_Y = int(
        (240 - 172) / 2
    )  # The display driver operates like a 240px width. The real display is 172px in the center.
    _NEOPIXEL = 8
    _NEOPIXEL_BYTE_ORDER = (1, 0, 2)  # Swap R and G
else:
    raise Exception(f"Unknown board model defined: {MODEL}")


def mac_2_str(mac, end_bytes=0):
    if end_bytes > 0:
        mac = mac[len(mac) - end_bytes :]
    return ":".join([f"{b:02X}" for b in mac]).upper()


def get_mac():
    return sta_if.config("mac")


def get_ip():
    return sta_if.ipconfig("addr4")[0]


def get_subnet_mask():
    return sta_if.ipconfig("addr4")[1]


class fullScreenMessage:
    """
    Display class for displaying a full screen message with icon
    """

    icon_label: lv.label = None
    text_label: lv.label = None
    scrn_full: lv.obj = None
    style: lv.style_t = lv.style_t()

    def __init__(self):
        self.style.init()

    # Symbols: https://docs.lvgl.io/master/details/main-components/font.html#special-fonts
    def display(
        self, msg=None, icon=lv.SYMBOL.WARNING, color=COLOR_WARNING, clear_screen=None
    ):
        """
        @param msg: Message to display below Icon. Set None to revert to the clear_screen screen.
        @param icon: LVGL Icon or Unicode str to display
        @param color: Hex color to color icon in.
        @param clear_screen: Screen to load on clearing a message screen. Defaults to the main scrn
        """
        if not msg:
            lv.screen_load(clear_screen if clear_screen else scrn)
            if self.scrn_full:
                del self.scrn_full
                self.scrn_err = None
                set_neopixel_rgb()  # Turn the neopixel off
            return

        elif not self.scrn_full:
            self.scrn_full = lv.obj()
            self.scrn_full.set_style_bg_color(lv.color_hex(0x220000), 0)

            self.icon_label = lv.label(self.scrn_full)

            self.style.set_text_font(lv.font_montserrat_48)

            self.icon_label.align(lv.ALIGN.CENTER, 0, -40)

            self.text_label = lv.label(self.scrn_full)
            self.text_label.align(lv.ALIGN.CENTER, 0, 30)

        self.style.set_text_color(lv.color_hex(color))
        self.icon_label.remove_style(self.style, lv.PART.MAIN)
        self.icon_label.add_style(self.style, lv.PART.MAIN)
        self.icon_label.set_text(icon)
        self.text_label.set_text(str(msg))

        lv.screen_load(self.scrn_full)

        # If we have a neopixel, make it match the icon color.
        set_neopixel_rgb(hex=color)


fullScreen = fullScreenMessage()


###
# SETUP ROUTINES
###


def setup_board():
    print("Setup_board")
    print(f"Setting CPU Freq to {_CPU_FREQ_HZ/1000000}MHz")
    print(f"Currently {machine.freq()/1000000}")
    machine.freq(_CPU_FREQ_HZ)
    if machine.freq() != 160000000:
        print(
            f"Failed to set CPU speed to {_CPU_FREQ_HZ}Hz, currently {machine.freq()}"
        )
    global wdt
    wdt = WDT(timeout=10000)
    wdt.feed()

    if _NEOPIXEL > -1:
        import neopixel

        global np
        np = neopixel.NeoPixel(machine.Pin(_NEOPIXEL), _NEOPIXEL_COUNT)

        # Cycle all the colors and then off.
        for color in LED_COLORS:
            set_neopixel_rgb(color)
            time.sleep(0.2)


display: display_driver_framework.DisplayDriver


def setup_display():
    """
    Setup Tally Display screen hardware bus and start the LVGL engine.
    Order of operations here is important for the display to initialize properly. Else, you may experience display snow/crash.
    """
    print("Setup_display: SPI")

    spi_bus = machine.SPI.Bus(host=_HOST, mosi=_MOSI, miso=_MISO, sck=_SCK)
    display_bus = lcd_bus.SPIBus(
        spi_bus=spi_bus,
        freq=_LCD_FREQ,
        dc=_DC,
        cs=_LCD_CS,
    )

    print("Setup_display: LVGL")
    if not lv.is_initialized():
        lv.init()
    else:
        lv.deinit()
        lv.init()

    print(f"Setup_display: display type: {_LCD_DRIVER_TYPE}")
    global display
    if _LCD_DRIVER_TYPE == "GC9A01":
        import gc9a01

        display_class = gc9a01.GC9A01

    elif _LCD_DRIVER_TYPE == "ST7789":
        import st7789

        display_class = st7789.ST7789

    display = display_class(
        data_bus=display_bus,
        display_width=_WIDTH,
        display_height=_HEIGHT,
        backlight_pin=_BL,
        color_space=lv.COLOR_FORMAT.RGB565,
        color_byte_order=_LCD_BYTE_ORDER,
        rgb565_byte_swap=_LCD_BYTE_COLOR_SWAP,
        offset_x=_LCD_OFFSET_X,
        offset_y=_LCD_OFFSET_Y,
    )

    display.set_power(True)
    display.init()
    display.set_backlight(100)

    display.set_rotation(_LCD_ROTATION)


import network

sta_if = network.WLAN(network.WLAN.IF_STA)


def setup_network():
    """
    Setup the WiFi connection and display status to the display.
    """
    print("Setup_network")
    if not sta_if.isconnected():
        print("connecting to network...")
        sta_if.active(True)
        try:
            # The username and password can be persisted to the ESP32 flash
            # Place SSID and (plain text) pass comma separated into 'wifi.txt'
            # REPL example:
            #  with open("wifi.txt", "w") as file:
            #     file.write("SSID_NAME,PassW0rd#")
            details = open("wifi.txt").read().split(",", 1)
            print("Connecting to: ", details)
            sta_if.connect(details[0], details[1])
        except OSError as e:
            print(e)
            fullScreen.display("No WiFi Details!")
            return
        except:
            fullScreen.display("Invalid WiFi Details!")
            return
        fullScreen.display(f"WIFI Connecting...\nSSID:{details[0]}", lv.SYMBOL.WIFI)
        while not sta_if.isconnected():
            wdt.feed()
            pass

        print("network config:", sta_if.ipconfig("addr4"))
        print(f"MAC ADDR: {mac_2_str(get_mac())}")
        fullScreen.display(
            f"WIFI Connected!\n{sta_if.ipconfig('addr4')[0]}", lv.SYMBOL.WIFI, COLOR_OK
        )
        time.sleep(2)
        fullScreen.display(None)
    return True


def _new_tally_cam():
    print("Setting Cam 1")
    fullScreen.display("Setting Cam 1", icon=lv.SYMBOL.PLUS, color=COLOR_OK)
    set_tally_camera(1)
    time.sleep(2)
    return 1


def setup_tally_camera():
    try:
        # The username and password can be persisted to the ESP32 flash
        # Place SSID and (plain text) pass comma separated into 'wifi.txt'
        # REPL example:
        #  with open("wifi.txt", "w") as file:
        #     file.write("SSID_NAME,PassW0rd#")
        details = open("tally_cam.txt", "r").read()
        print("Read tally cam: ", details)

        if not details:
            return _new_tally_cam()
        cam_number = int(details)

        if cam_number < 1 or cam_number > MAX_CAMERAS:
            raise ValueError("Cam number out of range")
        global CAMERA_NUMBER
        CAMERA_NUMBER = cam_number
    except OSError as e:
        return _new_tally_cam()
    except ValueError as e:
        print(e)
        print("Invalid Cam Number")
        fullScreen.display("Invalid Cam Number")
        time.sleep(2)
        return


def set_tally_camera(num: int):
    """
    Setup the WiFi connection and display status to the display.
    """
    print(f"Set tally camera: {num}")
    if num < 1 or num > MAX_CAMERAS:
        print(f"Invalid camera number set! {num}")
        return

    try:
        # The username and password can be persisted to the ESP32 flash
        # Place SSID and (plain text) pass comma separated into 'wifi.txt'
        # REPL example:
        #  with open("wifi.txt", "w") as file:
        #     file.write("SSID_NAME,PassW0rd#")
        open("tally_cam.txt", "w").write(str(num))
        global CAMERA_NUMBER
        CAMERA_NUMBER = num
    except OSError as e:
        print(e)
        fullScreen.display("Failed to write cam number!")
        return


def set_neopixel_rgb(rgb: list = LED_COLOR_OFF, hex: int = -1):
    """
    Set Neopixel (if available) to a certain color
    @param rgb: 3 part list of RGB colors.
    @param hex: hex color value to override rgb. Useful to set values from LCD consts.
    @returns bool: Whether this was actioned (e.g. if Neopixel was present)
    """
    if _NEOPIXEL > -1:
        # If we have a BGR neopixel rather than a RGB one
        new_rgb = [0, 0, 0]
        if hex > -1:
            r = (hex & 0xFF0000) >> 16
            g = (hex & 0x00FF00) >> 8
            b = hex & 0x0000FF
            rgb = [r, g, b]
        if _NEOPIXEL_BYTE_ORDER != [0, 1, 2]:
            print(
                f"Reordering neopixel from: {rgb} using byteorder: {_NEOPIXEL_BYTE_ORDER}"
            )
            # Reorder bytes based on the byte order defined.
            new_rgb[0] = rgb[_NEOPIXEL_BYTE_ORDER[0]]
            new_rgb[1] = rgb[_NEOPIXEL_BYTE_ORDER[1]]
            new_rgb[2] = rgb[_NEOPIXEL_BYTE_ORDER[2]]
        else:
            # Copies by reference, so we can't just set this above and override if different byte order.
            new_rgb = rgb
        # np Should be defined already in setup_board
        print(f"Setting neopixel to: {new_rgb}")
        np.fill(new_rgb)
        np.write()
        return True
    return False


import task_handler

th: task_handler.TaskHandler


def setup_task_handler():
    """
    Setup the task handler that handles any touchscreen events etc.
    """
    print("Setup_task_handler")
    try:
        global th
        th = task_handler.TaskHandler()
    except:
        print("Exception in task handler, restarting.")
        time.sleep(3)
        machine.reset()


def setup_scrn_main():
    """
    Setup the initial tally screen.
    """
    print("Setup_scrn_main")
    global scrn
    scrn = lv.screen_active()
    scrn.set_style_bg_color(lv.color_hex(0x000000), 0)


def setup():
    """
    Setup routines, run first on starting the script.

    """
    print("Setup")
    setup_board()
    setup_display()
    setup_task_handler()
    setup_scrn_main()
    if not setup_network():
        time.sleep(20)
        machine.reset()
    setup_tally_camera()


def main():
    """
    Main function
    """
    print("main")
    fullScreen.display("Waiting for data...", lv.SYMBOL.REFRESH)

    def event_handler(evt):
        code = evt.get_code()

        if code == lv.EVENT.CLICKED:
            print("Clicked event seen")
        elif code == lv.EVENT.VALUE_CHANGED:
            print("Value changed seen")

    # Display Camera Number label in the top centre of the screen
    btn_new = lv.button(scrn)
    btn_new.align(lv.ALIGN.TOP_MID, 0, 20)
    label = lv.label(btn_new)
    label.set_text("?")

    style_def = lv.style_t()
    style_def.init()
    style_def.set_text_color(lv.color_black())
    style_def.set_text_font(lv.font_montserrat_48)

    btn_new.add_event_cb(event_handler, lv.EVENT.ALL, None)

    label.add_style(style_def, lv.PART.MAIN)

    # Define an Arc to display the live / preview / standby status around the edge of the display
    style_arc_live = lv.style_t()
    style_arc_live.init()
    # Default to the preview style
    # It gets updated for live below.
    style_arc_live.set_arc_color(lv.color_hex(COLOR_PREV))

    style_arc_stdby = lv.style_t()
    style_arc_stdby.init()
    style_arc_stdby.set_arc_color(lv.color_hex(COLOR_STDBY))

    arc = lv.arc(scrn)
    arc.set_bg_angles(0, 360)
    arc.set_angles(0, 0)
    # Arcs start at about 3 o'clock, rotate it so we can put a nice cut out at the bottom of the arc instead.
    arc.set_rotation(125)
    arc.set_value(0)
    arc.center()
    # Make the arc the size of the screen border
    arc.set_size(_WIDTH, _HEIGHT)
    # Remove the arc touch knob
    arc.remove_style(None, lv.PART.KNOB)
    arc.add_style(style_arc_live, lv.PART.INDICATOR)
    arc.add_style(style_arc_stdby, lv.PART.MAIN)

    # Show mac addr at bottom of the screen
    label_id = lv.label(scrn)
    label_id.align(lv.ALIGN.BOTTOM_MID, 0, -20)
    label_id.set_text(mac_2_str(get_mac(), end_bytes=2))

    # Now to the main show, connect to a local socket server which sends demo camera numbers, update the display and arc
    import socket
    import json

    addr_info = socket.getaddrinfo("192.168.2.6", 8000)

    addr = addr_info[0][-1]

    s = None
    reconnect = True

    next_ping_time: int = time.ticks_ms() + PING_PERIOD_MS

    while True:
        # Feed the watchdog timer
        wdt.feed()

        if next_ping_time > 0 and time.ticks_ms() > next_ping_time:
            # Ping time hasn't been updated, we're not talking to the server...
            print("Ping timer exceeded")
            reconnect = True
            fullScreen.display("Ping time exceeded!")
            next_ping_time = -1
            time.sleep(2)
        # setup_network()
        try:
            if reconnect:
                if s:
                    s.close()
                    del s
                s = socket.socket()
                s.connect(addr)
                s.setblocking(True)
                s.settimeout(0.2)
                reconnect = False
                fullScreen.display(None)
                next_ping_time: int = time.ticks_ms() + PING_PERIOD_MS
            message_buffer = b""
            try:
                data = s.readline()
                if not data or data == b"":
                    continue
                message_buffer = data
            except KeyboardInterrupt as e:
                raise e
            except:
                continue

            print("*")
            # Parses the response into a JSON
            message: dict
            try:
                print(message_buffer)
                message = json.loads(message_buffer.decode())
            except:
                print(f"Invalid JSON recived from server: {message_buffer.decode()}")

            if (
                "MAC" in message
                and isinstance(message["MAC"], str)
                and message["MAC"].upper() != mac_2_str(get_mac())
            ):
                print("Ignoring command for other MAC addr")
                continue
            if CAMERA_NUMBER > 0:
                label.set_text(str(CAMERA_NUMBER))
                changed = False
                if "CAM_LIVE" in message and isinstance(message["CAM_LIVE"], int):
                    CAM_LIVE = int(message["CAM_LIVE"])
                    print(f"LIVE CAM: {CAM_LIVE}")
                    changed = True
                if "CAM_PREV" in message:
                    CAM_PREV = int(message["CAM_PREV"])
                    print(f"PREV CAM: {CAM_PREV}")
                    changed = True
                if changed:

                    arc_value = 0
                    if CAM_LIVE == CAMERA_NUMBER:
                        style_arc_live.set_arc_color(lv.color_hex(COLOR_LIVE))
                        arc_value = 100
                        set_neopixel_rgb(LED_COLOR_RED)
                        print("CAM LIVE")
                    elif CAM_PREV == CAMERA_NUMBER:
                        style_arc_live.set_arc_color(lv.color_hex(COLOR_PREV))
                        # Make a nice cut out for preview
                        arc_value = 80
                        set_neopixel_rgb(LED_COLOR_GREEN)
                        print("CAM PREVIEW")
                    else:
                        set_neopixel_rgb(LED_COLOR_OFF)
                        print("CAM STANDBY")

                    arc.remove_style(style_arc_live, lv.PART.INDICATOR)
                    arc.add_style(style_arc_live, lv.PART.INDICATOR)
                    arc.set_value(arc_value)
                if "IDENTIFY" in message:
                    for i in range(4):
                        fullScreen.display(
                            f"IDENTIFY\n{mac_2_str(get_mac())}\n{get_ip()}",
                            lv.SYMBOL.GPS,
                            COLOR_OK if i % 2 else COLOR_STDBY,
                        )
                        time.sleep(1)
                    fullScreen.display(None)
                if "PING" in message:
                    next_ping_time = time.ticks_ms() + PING_PERIOD_MS

            else:
                setup_tally_camera()
            if "SET_CAM" in message and isinstance(message["SET_CAM"], int):
                print("Seen SET_CAM")
                set_tally_camera(message["SET_CAM"])
        except ValueError:
            # TODO: This becomes b'' on socket failure, doesn't otherwise except.
            print(data)
            data = None
            continue
        except KeyboardInterrupt:
            raise
        except OSError as e:
            if e.args[0] == errno.EAGAIN:
                time.sleep(0.05)
                continue
            time.sleep(1)
            print(f"Got OS Error: {e}")
            print("Reconnecting")
            fullScreen.display(e)
            reconnect = True
        except Exception as e:
            print(e)
            time.sleep(1)


try:
    """
    Let's do this!
    """
    setup()
    main()

except KeyboardInterrupt:
    if display:
        display.set_backlight(0)
        display.set_power(False)
    set_neopixel_rgb()
    machine.reset()
except Exception as e:
    """
    Try to display the exception to the screen if we can!
    """
    fullScreen.display(str(e))
    raise e
