import functools
import os
import sys
import threading
import time
import tkinter as tk
from importlib import reload
from tkinter import simpledialog as dlg
from unittest import mock

from sensor import cycles, proxy, capturing, utils

out_dir = os.path.join("desktop", "photos")


def output_toggler(master, vent):
    def toggle():
        vent.toggle()
        lb_vent_state['text'] = str(vent)

    def ask_change_pin(e):
        pin_no = dlg.askinteger('New GPIOxx', 'Enter number of new GPIOxx for [%s] pin' % vent.name)
        if pin_no:
            vent.change_no(pin_no)
            lb_vent_state['text'] = str(vent)

    frame = tk.Frame(master)
    frame.pack(side='left')
    lb_vent_state = tk.Label(frame, text=str(vent))
    lb_vent_state.bind("<Button-1>", ask_change_pin)
    lb_vent_state.pack()

    btn_toggle = tk.Button(frame, text='Toggle', command=toggle)
    btn_toggle.pack()

    return vent, lb_vent_state


def enable_buttons(buttons, enable=True):
    for b in buttons:
        if enable:
            state = 'normal'
        else:
            state = 'disabled'
        b['state'] = state


class CycleThread(threading.Thread):

    def __init__(self, vents, on_start=None, on_stop=None, on_capture=None):
        super().__init__()
        self.stopped = False
        self.vents = vents

        def noop():
            pass

        self.on_start = on_start or noop
        self.on_stop = on_stop or noop
        self.on_capture = on_capture or noop

    def stop(self):
        self.stopped = True

    def run_cycle(self):
        for i in range(0, cycles.n_cycles):
            print("Executing cycle №%d" % (i + 1))

            sequence = cycles.get_cycle_vents([None] + self.vents, self.on_capture)

            for call in sequence:
                call()
                if self.stopped:
                    return

    def run(self):
        self.stopped = False
        self.on_start()
        self.run_cycle()
        self.on_stop()


def run(root, picameraapp=None):
    if picameraapp is None:
        picameraapp = mock.MagicMock()
        picameraapp.TakePicture = capturing.hq_capture
        picameraapp.CurrentImage = None
    else:
        root = tk.Frame(root)
        root.grid(row=2, column=0, columnspan=2, sticky='nsew')

    vent_manual = proxy.GPIOLed(cycles.manual_pin, name='Manual')

    vents = [proxy.GPIOLed(pin, 'K%d' % (i + 1)) for i, pin in enumerate(cycles.vent_pins)]

    flash_led = proxy.GPIOLed(cycles.flash_pin, name='Flash')
    pwm_led = proxy.PWMLed(cycles.hw_pwm_pin, name='PWM')

    if not proxy.camera_ok:
        lb_camera = tk.Label(root, text='Не удалось подключиться к камере')
        lb_camera.pack()

    frame = tk.Frame(root)
    frame.pack()

    output_toggler(frame, vent_manual)
    output_toggler(frame, pwm_led)

    togglers = [output_toggler(frame, vent) for vent in vents]

    frame2 = tk.Frame(root)
    frame2.pack()

    capture_is_flashing = tk.IntVar()
    capture_is_flashing.set(0)

    cb_flashing = tk.Checkbutton(frame2, text='Use flash with capture', variable=capture_is_flashing)
    cb_flashing.pack(side='left')

    host_capture = functools.partial(picameraapp.TakePicture, None)

    def use_flash_decorator(capture):
        def wrapped():
            _capture = capture
            if capture_is_flashing.get():
                _capture = capturing.flash_decorator(capture, cycles.flash_delays_us, flash_led)
            capture()

        return wrapped

    capture_cmd = use_flash_decorator(host_capture)

    bmp_or_jpg = tk.IntVar()
    bmp_or_jpg.set(0)

    def save_image():
        ext = 'jpg'
        if bmp_or_jpg.get():
            ext = 'bmp'

        folder, path = utils.image_save_to(out_dir, ext)
        os.makedirs(folder, exist_ok=True)

        if picameraapp.CurrentImage is None:
            print("No picture to save!")
        else:
            print("Saving picture to %s..." % path)
            picameraapp.CurrentImage.save(path, quality=95)

    def thread_on_start():
        buttons = [btn_capture, btn_captures, btn_save]
        enable_buttons(buttons, False)
        btn_cycle['text'] = 'Stop'
        btn_cycle.bind("<Button-1>", th_wrapper.stop)

    def thread_on_stop():
        buttons = [btn_capture, btn_captures, btn_save]
        enable_buttons(buttons, True)
        btn_cycle['text'] = 'Cycle'
        btn_cycle.bind("<Button-1>", th_wrapper.start)

        for vent, label in togglers:
            vent.off()
            label['text'] = str(vent)
            time.sleep(0.1)

    use_capture_in_cycle = tk.IntVar()
    use_capture_in_cycle.set(1)

    def capture_save_cmd():
        capture_cmd()
        save_image()

    def thread_on_capture():
        if use_capture_in_cycle.get():
            capture_save_cmd()

    class ThreadWrapper:
        thread = None

        def start(self, e=None):
            self.thread = CycleThread(vents,
                                      on_start=thread_on_start,
                                      on_stop=thread_on_stop,
                                      on_capture=thread_on_capture)
            self.thread.start()

        def stop(self, e=None):
            self.thread.stop()

    th_wrapper = ThreadWrapper()

    cb_usecaptureincycle = tk.Checkbutton(frame2, text='Use capture in cycle', variable=use_capture_in_cycle)
    cb_usecaptureincycle.pack(side='left')

    btn_cycle = tk.Button(frame2, text='Cycle', command=th_wrapper.start)
    btn_cycle.pack(side='left')

    btn_capture = tk.Button(frame2, text='Capture', command=capture_cmd)
    btn_capture.pack(side='left')
    # btn_aci = tk.Button(frame2, text='Search', command=intensity_search_cmd)
    # btn_aci.pack(side='left')

    btn_captures = tk.Button(frame2, text='Capture & Save', command=capture_save_cmd)
    btn_captures.pack(side='left')
    btn_save = tk.Button(frame2, text='Save', command=save_image)
    btn_save.pack(side='left')

    def reload_cycles():
        reload(cycles)
        pwm_led.change_no(cycles.hw_pwm_pin)
        flash_led.change_no(cycles.flash_pin)

    btn_reload = tk.Button(frame2, text='Reload', command=reload_cycles)
    btn_reload.pack(side='left')


def standalone():
    root = tk.Tk()
    root.geometry("600x400")

    run(root)
    root.mainloop()


def hosted():
    picam_path = os.path.join("thirdparty", "PiCameraApp", "Source")
    sys.path.insert(0, picam_path)
    import PiCameraApp
    os.chdir(picam_path)
    PiCameraApp.Run(run)


if __name__ == "__main__":
    # standalone()
    hosted()
