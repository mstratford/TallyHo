#!/usr/bin/env python
"""
TallyHo Client Bootloader for ESP32 MicroPython with LVGL

Works as a successful boot watchdog.

If boot of the main tally program fails to complete the main loop (or we repeatedly reset the board), it will enter the REPL.
Allows regaining control for REPL-based file flashing during a boot loop.
"""

LAUNCH_REPL = False
CONFIG_BOOT_SUCCESS = "config/unsuccessful_boots"
print("\n\n**** Welcome to the TallyHo bootloader! ****\n\n")

main_path = "tally.py"
print(f"Trying to read {main_path}")
try:
    open(main_path, "r")
    # continue with the file.
except OSError:  # open failed
    print(
        f"""
  File not found.
  Use Ctrl-E / Ctrl-D to paste in the {main_path} file so it can bootload itself.
  Exiting to REPL.
    """
    )
    LAUNCH_REPL = True


def try_boot():
    # Source code exists
    # Stop us from booting into it if it seems like it's continuously crashing.
    content = ""
    try:
        file = open(CONFIG_BOOT_SUCCESS, "r")
        content = file.read()
        file.close()

    except OSError:  # open failed
        content = "-2"  # Never booted before

    try:
        tries = int(content.strip())
    except:
        tries = -2
    file = open(CONFIG_BOOT_SUCCESS, "w")
    if tries == -2:
        # Doesn't look like we've booted fresh before.
        # Start a counter
        print("First boot!")
        tries = 0
    elif tries == -1:
        print("Last boot seemed successful!")
        # Looks like we started nicely enough to be able to update firmware remotely, allow normal start!
    else:
        # We didn't get to the bit in the main script where we've completed a successful loop
        print("Failed start detected!")
        tries += 1  # We just restarted, count this as a try
        print(f"Unsuccessful attempts: {tries}")
        if tries > 3:

            # We didn't get to the bit in the main script where we've completed a successful loop after many attempts.
            # Likely means we crashed.
            print(
                "Failure to start several times, exiting to REPL for reprogramming / debug!\n\n"
            )
            global LAUNCH_REPL
            LAUNCH_REPL = True
            file.write(
                "-2"
            )  # Reset so that it will try again on next boot (maybe after updating the tally file.)
            file.close()
            return

        print("Trying again.")

    file.write(str(tries))
    file.close()
    print("\n\n**** Tally Ho! ****\n\n")
    import tally


if not LAUNCH_REPL:
    try_boot()

# We didn't launch into tally, so implicitly launch into REPL
