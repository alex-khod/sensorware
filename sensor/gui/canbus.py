""" Simple gui for testing canbus commands """

import tkinter as tk

from sensor.canbus import app
from sensor.canbus import flashing
from sensor.canbus.requests import REQUEST
from sensor.canbus.shutdown import SHUTDOWN_TYPE


def capture_buttons_frame(frame, can_app):
    frame.pack(side='left')

    tk.Button(frame, text='ENABLE CAPTURE', command=lambda: can_app.cmd_set_allow_capture(True)).pack()
    tk.Button(frame, text='DISABLE CAPTURE', command=lambda: can_app.cmd_set_allow_capture(False)).pack(fill="x")
    tk.Button(frame, text='FORCE CAPTURE', command=lambda: can_app.cmd_set_allow_capture(can_app.FORCE_CAPTURE)).pack()
    tk.Button(frame, text='ENABLE DEFAULT CAPTURE', command=lambda: can_app.cmd_set_default_allow_capture(True)).pack()
    tk.Button(frame, text='DISABLE DEFAULT CAPTURE',
              command=lambda: can_app.cmd_set_default_allow_capture(False)).pack()


def send_states_frame(frame, can_app):
    frame.pack(side='left')

    tk.Button(frame, text='ENABLE SEND_STATES', command=lambda: can_app.cmd_set_send_states(True)).pack()
    tk.Button(frame, text='DISABLE SEND_STATES', command=lambda: can_app.cmd_set_send_states(False)).pack()
    tk.Button(frame, text='ENABLE DEFAULT SEND_STATES',
              command=lambda: can_app.cmd_set_default_send_states(True)).pack()
    tk.Button(frame, text='DISABLE DEFAULT SEND_STATES',
              command=lambda: can_app.cmd_set_default_send_states(False)).pack()
    tk.Button(frame, text='ENABLE REQUESTS', command=lambda: setattr(can_app, 'send_requests', True)).pack()
    tk.Button(frame, text='DISABLE REQUESTS', command=lambda: setattr(can_app, 'send_requests', False)).pack()


def get_param_frame(frame, can_app):
    frame.pack(side="left")

    def get_param_cmd(param_id):
        return lambda: can_app.cmd_get_param(param_id)

    tk.Button(frame, text='GET  P', command=get_param_cmd(0)).pack()
    tk.Button(frame, text='GET dP', command=get_param_cmd(1)).pack()
    tk.Button(frame, text='GET  P THRESH', command=get_param_cmd(2)).pack()
    tk.Button(frame, text='GET dP THRESH', command=get_param_cmd(3)).pack()


def value_setter(master, label_text, text_handler):
    """ Text + submit button"""
    frame = tk.Frame(master)
    frame.pack()
    var = tk.StringVar()
    tk.Entry(frame, textvariable=var).pack(side='left')
    tk.Button(frame, text=label_text, command=lambda: text_handler(var.get())).pack(side='left')


def set_param_frame(frame, can_app):
    frame.pack(side='left')

    def set_param_cmd(param_id):
        return lambda text: can_app.cmd_set_param(param_id, text)

    value_setter(frame, 'SET  P THRESH', text_handler=set_param_cmd(2))
    value_setter(frame, 'SET dP THRESH', text_handler=set_param_cmd(3))
    value_setter(frame, 'SET MIN DELAY', text_handler=set_param_cmd(4))


def flashing_frame(frame, can_app):
    frame.pack(side='left')

    def prepare():
        flashing.prepare()
        print("Flash archive has been created")

    tk.Button(frame, text='PREPARE FLASH', command=prepare).pack()
    tk.Button(frame, text='TRANSFER FLASH', command=lambda: can_app.cmd_req([REQUEST.UPLOAD, 0])).pack()
    tk.Button(frame, text='EXEC FLASH', command=lambda: can_app.cmd_req([REQUEST.SHUTDOWN, SHUTDOWN_TYPE.FLASH])).pack()
    tk.Button(frame, text='RESTORE BACKUP',
              command=lambda: can_app.cmd_req([REQUEST.SHUTDOWN, SHUTDOWN_TYPE.RESTORE])).pack()
    tk.Button(frame, text='SHUTDOWN', command=lambda: can_app.cmd_shutdown()).pack()
    tk.Button(frame, text='REBOOT', command=lambda: can_app.cmd_reboot()).pack()


def db_frame(frame, can_app):
    frame.pack(side='left')
    tk.Button(frame, text='ENUM DB', command=can_app.cmd_enum_db).pack()
    value_setter(frame, 'REQUEST DB', lambda text: can_app.cmd_get_file(int(text)))
    value_setter(frame, 'CLEAR DB', lambda text: can_app.cmd_clear_db(int(text)))


def gui(can_app):
    root = tk.Tk()
    root.geometry("800x300")

    row = tk.Frame(root)
    row.pack()
    capture_buttons_frame(tk.Frame(row), can_app)
    send_states_frame(tk.Frame(row), can_app)
    get_param_frame(tk.Frame(row), can_app)
    flashing_frame(tk.Frame(row), can_app)

    row = tk.Frame(root)
    row.pack(pady=10)
    set_param_frame(tk.Frame(row), can_app)
    db_frame(tk.Frame(row), can_app)

    def walk_gui_tree(root, callback):
        for ch in root.children.values():
            callback(ch)
            walk_gui_tree(ch, callback)

    walk_gui_tree(root, callback=lambda x: x.config(padx=4) if isinstance(x, tk.Frame) else x.config(width=24))

    root.mainloop()


def gui_app():
    ecu, cnt = app.init_app(client_mode=True)
    gui(cnt)
    cnt.stop()
    ecu.disconnect()


if __name__ == "__main__":
    gui_app()
