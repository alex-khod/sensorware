import functools
import threading
import time

from skimage import color

from sensor import cycles, exc, proxy


class FlashThread(threading.Thread):

    def __init__(self, delays_us, flash_led, **kwargs):
        self.delays_us = delays_us
        self.led = flash_led
        super().__init__(**kwargs)

    def flash(self):
        delays_sec = [x / 1e6 for x in self.delays_us]
        time.sleep(delays_sec[0])
        self.led.on()
        time.sleep(delays_sec[1])
        self.led.off()
        time.sleep(0.1)

    def run(self):
        start = time.time()
        self.flash()
        duration_ms = (1000 * (time.time() - start))
        print("Flash duration:%.3f (ms)" % duration_ms)


def flash_decorator(capture_func, flash_delays_us, flash_led):
    def wrapped():
        flash_thread = FlashThread(flash_delays_us, flash_led)
        flash_thread.start()
        result = capture_func()
        flash_thread.join()
        return result

    return wrapped


def resolution_capture_func(resolution, use_video_port):
    def capture_func(camera):
        rgb = proxy.picamera.array.PiRGBArray(camera, size=resolution)
        array = camera.capture(rgb, 'rgb', use_video_port=use_video_port, resize=resolution)
        if array is not None:
            # mock camera output
            return array
        # real camera output
        return rgb.array

    return capture_func


lq_capture = resolution_capture_func(resolution=(320, 240), use_video_port=True)
hq_capture = resolution_capture_func(resolution=(1312, 976), use_video_port=False)

flash_delays_us = (int(0.0 * 1e6), int(0.8 * 1e6))


def image_mean_intensity(capture_func):
    rgb_arr = capture_func()
    mean = (255 * color.rgb2gray(rgb_arr)).astype('uint8').mean()
    return mean


def sequence_mean_intensity(capture_func, length=3):
    values = [image_mean_intensity(capture_func) for _ in range(length)]
    mean = sum(values) / len(values)
    return mean


class IntensitySearch:

    def __init__(self, camera, flash_led=None, start_duty=cycles.hw_pwm_duty, duty_step=cycles.hw_pwm_duty_step):
        self.duty = start_duty
        flash_led = flash_led or proxy.PWMLed(cycles.hw_pwm_pin)
        self.flash_led = flash_led
        self.duty_step = duty_step
        measurement_capture = functools.partial(lq_capture, camera)
        self.measurement_capture = flash_decorator(measurement_capture, flash_delays_us, flash_led)

        _hq_capture = functools.partial(hq_capture, camera)
        self.hq_capture = flash_decorator(_hq_capture, flash_delays_us, flash_led)

    def setup_and_measure(self, duty):
        self.duty = duty
        self.flash_led.led.setup(cycles.hw_pwm_freq, duty)
        mean = sequence_mean_intensity(self.measurement_capture)
        return mean

    def search(self):
        """ Search pwm_duty for flash_led that gives mean image intensity within required margins"""

        def is_zigzag(old_intensity, new_intensity):
            is_above_max = new_intensity > max_light
            is_below_min = new_intensity > min_light
            was_above_max = old_intensity > max_light
            was_below_min = old_intensity < min_light
            return (was_below_min and is_above_max) or (was_above_max and is_below_min)

        duty = self.duty
        duty_step = self.duty_step
        mi = self.setup_and_measure(duty)

        min_light, max_light = cycles.min_mean_light_intensity, cycles.max_mean_light_intensity
        min_duty, max_duty = cycles.hw_pwm_duty_min, cycles.hw_pwm_duty_max

        while not (min_light <= mi <= max_light):
            if mi < min_light:
                duty += duty_step
            else:
                duty -= duty_step

            if duty > max_duty:
                # raise exc.ExceptionDutyUpperLimitReached
                return mi
            elif duty < min_duty:
                raise exc.ExceptionDutyLowerLimitReached

            new_mi = self.setup_and_measure(duty)
            print('L:%d; newL:%d; z:%d; dz:%d' % (mi, new_mi, duty, duty_step))

            if is_zigzag(mi, new_mi):
                # current duty step doesn't allow to reach required light interval - halve the step
                duty_step = int(duty_step / 2)
            mi = new_mi
        print('Final MI: %.3f @ z==' % mi, duty)
        return mi

    def capture(self):
        self.search()
        rgb = self.hq_capture()
        return rgb


search = None


def default_search_capture(camera):
    global search
    if search is None:
        search = IntensitySearch(camera)
    rgb = search.capture()
    return rgb
