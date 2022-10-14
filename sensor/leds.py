from sensor import cycles, exc

vent_states = {True: 'Вкл.', False: 'Выкл.'}

default_gpio_no = 13


class DigitalOutput:
    """
        Base class for digital on/off output.
    """
    led_factory = None

    def __init__(self, gpio_no=default_gpio_no, name='', led_factory=None):
        self.gpio_no = gpio_no
        self.name = name
        self._is_active = False
        self.led_factory = led_factory
        self.led = None
        self.create_led()

    def create_led(self):
        self.led = self.led_factory(self.gpio_no)

    def destroy_led(self):
        if self.led is not None:
            if self.is_active:
                self.off()
            self.led = None

    def on(self):
        self._is_active = True
        self.led.on()

    def off(self):
        self._is_active = False
        self.led.off()

    @property
    def is_active(self):
        return self._is_active

    def toggle(self):
        if self.is_active:
            self.off()
        else:
            self.on()

    def __str__(self):
        return "[%s] GPIO%d = %s" % (self.name, self.gpio_no, vent_states[self.is_active])

    def change_no(self, gpio_no):
        if self.is_active:
            self.off()
        self.destroy_led()
        self.gpio_no = gpio_no
        self.create_led()
        print('Contact "%s" set to pin %d' % (self.name, gpio_no))


def gpio_led_factory(gpio_no, gpiozero):
    return gpiozero.LED(gpio_no, active_high=cycles.active_high, pin_factory=None)


class MockLED:

    def __init__(self, gpio_no):
        self.gpio_no = gpio_no

    def on(self):
        print('Fake led at GPIO%s is on' % (self.gpio_no))

    def off(self):
        print('Fake led at GPIO%s is off' % (self.gpio_no))

    def setup(self, freq, duty):
        print('Fake led freq=%d, duty=%d' % (freq, duty))


def mock_led_factory(gpio_no):
    return MockLED(gpio_no)


class PWMLED:
    duty = 0
    freq = 0

    def __init__(self, gpio_no, pigpio):
        self.gpio_no = gpio_no
        self.pigpio = pigpio

    def setup(self, freq, duty):
        if not (cycles.hw_pwm_duty_min <= duty <= cycles.hw_pwm_duty_max):
            raise exc.ExceptionBadDuty
        self.freq = freq
        self.duty = duty

    def on(self):
        self.pigpio.hardware_PWM(self.gpio_no, self.freq, self.duty)

    def off(self):
        self.pigpio.hardware_PWM(self.gpio_no, 0, 0)


def pwm_led_factory(gpio_no, pigpio):
    pwm_led = PWMLED(gpio_no, pigpio)
    pwm_led.setup(freq=cycles.hw_pwm_freq, duty=cycles.hw_pwm_duty)
    return pwm_led
