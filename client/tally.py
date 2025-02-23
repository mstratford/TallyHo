#!/usr/bin/env python
"""
TallyHo Client for ESP32 MicroPython with LVGL
"""
import lcd_bus

# from lvgl_micropython import display_driver_framework
from micropython import const
import machine
from time import sleep
import errno

# display settings
_WIDTH = const(240)
_HEIGHT = const(240)
_BL = const(3)
_RST = const(4)
_DC = const(2)
_MOSI = const(7)
_MISO = const(-1)
_SCK = const(6)
_HOST = const(1)  # SPI2

_LCD_CS = const(10)
_LCD_FREQ = const(80000000)  # const(80000000)

_LCD_BYTE_ORDER_RGB = const(0x00)
_LCD_BYTE_ORDER_BGR = const(0x08)

_LCD_BYTE_COLOR_SWAP = True

_TOUCH_CS = const(18)
_TOUCH_FREQ = const(10000000)


COLOR_WARNING = 0xFF6600
COLOR_OK = 0x007700

COLOR_LIVE = 0xFF0000
COLOR_PREV = COLOR_OK
COLOR_STDBY = 0x222222

CAMERA_NUMBER = 1
# LVGL display engine
import lvgl as lv

# The main lvgl Tally Screen
scrn: lv.obj = None


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
            if not clear_screen:
                lv.screen_load(clear_screen if clear_screen else scrn)
            if self.scrn_full:
                del self.scrn_full
                self.scrn_err = None
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


fullScreen = fullScreenMessage()


###
# SETUP ROUTINES
###

display: display_driver_framework.DisplayDriver


def setup_display():
    """
    Setup Tally Display screen hardware bus and start the LVGL engine.
    Order of operations here is important for the display to initialize properly. Else, you may experience display snow/crash.
    """
    print("Setup_display: SPI")
    import gc9a01

    spi_bus = machine.SPI.Bus(host=_HOST, mosi=_MOSI, miso=_MISO, sck=_SCK)
    # spi_bus =
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

    print("Setup_display: display")
    global display
    display = gc9a01.GC9A01(
        data_bus=display_bus,
        display_width=_WIDTH,
        display_height=_HEIGHT,
        backlight_pin=_BL,
        color_space=lv.COLOR_FORMAT.RGB565,
        color_byte_order=_LCD_BYTE_ORDER_BGR,
        rgb565_byte_swap=_LCD_BYTE_COLOR_SWAP,
    )

    display.set_power(True)
    display.init()
    display.set_backlight(100)


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
            pass

        print("network config:", sta_if.ipconfig("addr4"))
        fullScreen.display(
            f"WIFI Connected!\n{sta_if.ipconfig('addr4')[0]}", lv.SYMBOL.WIFI, COLOR_OK
        )
        sleep(2)
        fullScreen.display(None)
    return True


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
        sleep(3)
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
    setup_display()
    setup_task_handler()
    setup_scrn_main()
    if not setup_network():
        sleep(20)
        machine.reset()


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

    # Display a demo label in the centre of the screen
    btn_new = lv.button(scrn)
    btn_new.align(lv.ALIGN.CENTER, 0, 0)
    label = lv.label(btn_new)
    label.set_text("Loading...")

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

    # Now to the main show, connect to a local socket server which sends demo camera numbers, update the display and arc
    import socket

    addr_info = socket.getaddrinfo("192.168.2.6", 8000)

    addr = addr_info[0][-1]

    s = None
    reconnect = True
    while True:
        setup_network()
        try:
            if reconnect:
                if s:
                    del s
                s = socket.socket()
                s.connect(addr)
                s.setblocking(False)
                reconnect = False
                fullScreen.display(None)
            data = s.recv(1)
            value = int(data)
            print(f"Got {value}")

            if value == CAMERA_NUMBER:
                style_arc_live.set_arc_color(lv.color_hex(COLOR_LIVE))
            else:
                style_arc_live.set_arc_color(lv.color_hex(COLOR_PREV))

            arc_value = 0
            # Basic demo of Preview and Program
            if value == CAMERA_NUMBER:
                arc_value = 100
            elif value == 2:
                # Make a nice cut out for preview
                arc_value = 80
            arc.remove_style(style_arc_live, lv.PART.INDICATOR)
            arc.add_style(style_arc_live, lv.PART.INDICATOR)
            arc.set_value(arc_value)
            label.set_text(f"Camera {value}")
        except ValueError:
            # TODO: This becomes b'' on socket failure, doesn't otherwise except.
            print(data)
            data = None
            continue
        except KeyboardInterrupt:
            raise
        except OSError as e:
            if e.args[0] == errno.EAGAIN:
                sleep(0.05)
                continue
            sleep(1)
            print(f"Got OS Error: {e}")
            print("Reconnecting")
            fullScreen.display(e)
            reconnect = True
        except Exception as e:
            print(e)
            sleep(1)


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
    machine.reset()
except Exception as e:
    """
    Try to display the exception to the screen if we can!
    """
    fullScreen.display(str(e))
    raise e
