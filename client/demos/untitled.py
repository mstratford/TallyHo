import lcd_bus
from micropython import const
import machine
from time import sleep

import fs_driver
import sys


# display settings
_WIDTH = const(240)
_HEIGHT = const(240)
_BL = const(3)
_RST = const(4)
_DC = const(2)  # 5
_MOSI = const(7)
_MISO = const(-1)
_SCK = const(6)
_HOST = const(1)  # SPI2

_LCD_CS = const(10)
_LCD_FREQ = const(800000)  # const(80000000)

_TOUCH_CS = const(18)
_TOUCH_FREQ = const(10000000)

spi_bus = machine.SPI.Bus(host=_HOST, mosi=_MOSI, miso=_MISO, sck=_SCK)
# spi_bus =
display_bus = lcd_bus.SPIBus(
    spi_bus=spi_bus,
    freq=_LCD_FREQ,
    dc=_DC,
    cs=_LCD_CS,
)
# from spi3wire import Spi3Wire

# spi_3_wire = Spi3Wire(scl=_SCK, sda=_MOSI, cs=_LCD_CS, freq=_LCD_FREQ, spi_mode=0)

# display_bus = lcd_bus.SPIBus(spi_bus=spi_3_wire, freq=_LCD_FREQ, dc=_DC, cs=_LCD_CS)
import gc9a01
import lvgl as lv

if not lv.is_initialized():
    lv.init()
else:
    lv.deinit()
    lv.init()
#        scl: int,
#        sda: int,
#        cs: int,
#        freq: int,
#        spi_mode: int = 0,
#        use_dc_bit: bool = True,
#        dc_zero_on_data: bool = False,
#        lsb_first: bool = False,
#        cs_high_active: bool = False,
#        del_keep_cs_inactive: bool = False,
th = None
try:
    display = gc9a01.GC9A01(
        data_bus=display_bus,
        display_width=_WIDTH,
        display_height=_HEIGHT,
        backlight_pin=_BL,
        color_space=lv.COLOR_FORMAT.RGB565,
    )

    display.set_power(True)
    display.init()
    display.set_backlight(100)

    import task_handler

    th = task_handler.TaskHandler()

    scrn = lv.screen_active()
    scrn.set_style_bg_color(lv.color_hex(0x000000), 0)

    def event_handler(evt):
        code = evt.get_code()

        if code == lv.EVENT.CLICKED:
            print("Clicked event seen")
        elif code == lv.EVENT.VALUE_CHANGED:
            print("Value changed seen")

    btn_new = lv.button(scrn)
    btn_new.align(lv.ALIGN.CENTER, 0, 0)
    label = lv.label(btn_new)
    label.set_text("Untitled.mov")

    style_def = lv.style_t()
    style_def.init()
    style_def.set_text_color(lv.color_black())
    # style_def.set_text_font(lv.font_montserrat_16, lv.PART.SELECTED)

    btn_new.add_event_cb(event_handler, lv.EVENT.ALL, None)

    btn_new.set_style_text_font(lv.font_montserrat_16, 0)

    label.add_style(style_def, 0)
    # slider = lv.slider(scrn)
    # slider.set_size(150, 50)
    # slider.center()

    # display.reset()
    # hello
    # del display
except Exception as e:
    raise e

while True:
    sleep(1)
