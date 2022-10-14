""" Simple gui to test switching vents on/off """
import threading
import time
import tkinter as tk
from tkinter import simpledialog as dlg

from sensor import proxy, cycles, mocks


class ButtonThread(threading.Thread):
    stopped = False

    def run(self):
        button = proxy.Button(4, pull_up=None, active_state=True)
        while not self.stopped:
            if button.is_pressed:
                print("GPIO 4 HIGH")
            else:
                print("GPIO 4 LOW")
            if isinstance(button, mocks.MockButton):
                time.sleep(1)


def output_toggler(master, output):
    def toggle():
        output.toggle()
        lb_vent_state['text'] = str(output)

    def ask_change_pin(e):
        pinno = dlg.askinteger('New GPIOxx', 'Enter number of new GPIOxx for [%s] pin' % output.name)
        if pinno:
            output.change_no(pinno)
            lb_vent_state['text'] = str(output)

    frame = tk.Frame(master)
    frame.pack(side='left')
    lb_vent_state = tk.Label(frame, text=str(output))
    lb_vent_state.bind("<Button-1>", ask_change_pin)
    lb_vent_state.pack()

    btn_toggle = tk.Button(frame, text='Toggle', command=toggle)
    btn_toggle.pack()

    return output, lb_vent_state


def app():
    root = tk.Tk()
    root.geometry("800x150")

    frame = root

    vent_manual = proxy.GPIOLed(cycles.manual_pin, name='Manual')

    pwm_led = proxy.PWMLed(cycles.hw_pwm_pin, name='PWM')

    output_toggler(frame, vent_manual)
    output_toggler(frame, pwm_led)

    vents = [proxy.GPIOLed(pin, 'K%d' % (i + 1)) for i, pin in enumerate(cycles.vent_pins)]

    for vw in vents:
        output_toggler(frame, vw)

    btn_thread = ButtonThread()
    btn_thread.start()

    root.mainloop()
    btn_thread.stopped = True
    btn_thread.join()


if __name__ == '__main__':
    app()
