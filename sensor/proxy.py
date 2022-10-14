import functools
import platform

from sensor import leds
from sensor import mocks


def is_windows():
    return platform.system() == "Windows"


def is_ubuntu():
    return platform.system() == "Linux" and platform.linux_distribution()[0] == "Ubuntu"


def import_leds():
    import gpiozero
    gpio_led_factory = functools.partial(leds.gpio_led_factory, gpiozero=gpiozero)
    import pigpio
    pigpio = pigpio.pi()
    pwm_led_factory = functools.partial(leds.pwm_led_factory, pigpio=pigpio)
    mock_led_factory = leds.mock_led_factory

    return gpiozero.Button, gpio_led_factory, pwm_led_factory, mock_led_factory


if is_windows() or is_ubuntu():
    Button = mocks.MockButton
    bustype = "virtual"
    gpio_led_factory, pwm_led_factory, mock_led_factory = [leds.mock_led_factory for _ in range(3)]
else:
    bustype = "socketcan"
    Button, gpio_led_factory, pwm_led_factory, mock_led_factory = import_leds()

GPIOLed = functools.partial(leds.DigitalOutput, led_factory=gpio_led_factory)
PWMLed = functools.partial(leds.DigitalOutput, led_factory=pwm_led_factory)

camera_ok = False


def get_real_camera():
    import picamera as _picamera
    camera = _picamera.PiCamera(sensor_mode=1)
    return _picamera, camera


def try_get_camera():
    try:
        picamera, camera = get_real_camera()
        print('Camera success...')
        global camera_ok
        camera_ok = True
        return picamera, camera
    except ImportError:
        print("Can't load camera: mocked...")
        return mocks.mock.MagicMock(), mocks.camera_mock


picamera, camera = try_get_camera()
