import math
from sensor import cycles, proxy

from scipy.stats import logistic
from sensor import capturing


def sigmoid(x):
    s = 1 / (1 + math.exp(-x))
    return s


def get_func(func, a, b):
    def intensity_func(x):
        s = 2 * 255 * (func(x / a) - 0.5)

        return s

    return intensity_func


get_mean_intensity = get_func(logistic.cdf, 25000, 0)


def get_vals():
    print(get_mean_intensity(5000))
    print(get_mean_intensity(7500))
    print(get_mean_intensity(50000))


search = capturing.IntensitySearch(camera=proxy.camera)

cycles.hw_pwm_duty = 5500
cycles.hw_pwm_duty_step = 400000
cycles.hw_pwm_duty_min = 5000
cycles.hw_pwm_duty_max = 500000

cycles.min_mean_light_intensity = 150
cycles.max_mean_light_intensity = 160
mn, mx = cycles.min_mean_light_intensity, cycles.max_mean_light_intensity
print('min, max', mn, mx)
search.search()

cycles.min_mean_light_intensity = 143
cycles.max_mean_light_intensity = 144
mn, mx = cycles.min_mean_light_intensity, cycles.max_mean_light_intensity
print('min, max', mn, mx)
search.search()

cycles.min_mean_light_intensity = 255
cycles.max_mean_light_intensity = 256
mn, mx = cycles.min_mean_light_intensity, cycles.max_mean_light_intensity

print('min, max', mn, mx)
search.search()

cycles.min_mean_light_intensity = -2
cycles.max_mean_light_intensity = -1
mn, mx = cycles.min_mean_light_intensity, cycles.max_mean_light_intensity

print('min, max', mn, mx)
search.search()
