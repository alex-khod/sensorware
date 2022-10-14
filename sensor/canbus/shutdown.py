import os

from sensor.canbus import flashing
from sensor.canbus.requests import REQUEST
from sensor.canbus.transfer import TRANSFER


class SHUTDOWN_TYPE:
    SHUTDOWN = 0
    REBOOT = 1
    FLASH = 2
    RESTORE = 3


class ShutdownHandler:

    def __init__(self, can_app):
        self.can_app = can_app
        self.shutdown_type = SHUTDOWN_TYPE.REBOOT
        self.shutting_down = False
        self.ready_for_shutdown = False
        self.sent_shutdown = False

    def process(self, arg_id):
        self.shutdown_type = arg_id
        shutdowns = {
            SHUTDOWN_TYPE.SHUTDOWN: "shutdown",
            SHUTDOWN_TYPE.REBOOT: "reboot",
            SHUTDOWN_TYPE.FLASH: "flash",
            SHUTDOWN_TYPE.RESTORE: "restore",
        }
        try:
            shutdown_name = shutdowns[self.shutdown_type]
            if self.shutdown_type == SHUTDOWN_TYPE.FLASH:
                if not os.path.isfile(flashing.FLASH_IN_PATH):
                    print('Flash file not found')
                    self.can_app.cmd_res([REQUEST.SHUTDOWN, TRANSFER.FLASH_ERROR])
                    return
            if self.shutdown_type == SHUTDOWN_TYPE.RESTORE:
                if not os.path.isfile(flashing.BACKUP_PATH):
                    print('Backup file not found')
                    self.can_app.cmd_res([REQUEST.SHUTDOWN, TRANSFER.FLASH_ERROR])
                    return
            self.can_app.cmd_res([REQUEST.SHUTDOWN, 0])
            print('Preparing for ' + shutdown_name)
            self.shutting_down = True
        except KeyError:
            self.can_app.cmd_res([REQUEST.SHUTDOWN, TRANSFER.ERROR])

    def callback(self):
        if self.shutting_down:
            if self.ready_for_shutdown:
                if not self.sent_shutdown:
                    self.can_app.cmd_res([REQUEST.SHUTDOWN, TRANSFER.OK])
                    self.sent_shutdown = True
                if self.shutdown_type == SHUTDOWN_TYPE.SHUTDOWN:
                    os.system('shutdown now')
                    os.system('systemctl poweroff -i')
                elif self.shutdown_type == SHUTDOWN_TYPE.FLASH:
                    flashing.reflash()
                    os.system("reboot")
                elif self.shutdown_type == SHUTDOWN_TYPE.RESTORE:
                    flashing.restore()
                    os.system("reboot")
                else:
                    os.system('reboot')
                return False
