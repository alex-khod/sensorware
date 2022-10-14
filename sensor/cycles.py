"""
    Module used as a user config file.
"""
import time

# Клапан 1 = IN4 = GPIO22 (PIN8)
# Клапан 2 = IN3 = GPIO27 (PIN7)
# Клапан 3 = IN1 = GPIO17 (PIN6)

# Начальное напряжение контакта - низкое
# active_high = False

# Начальное напряжение контакта - высокое
active_high = True

# [мкс] задержки перед вспышкой, после вспышки
flash_delays_us = 0, 2000000

# (gpio) пин светодиода подсветки
flash_pin = 12

# пин, частота и коэфициент заполнения аппаратного ШИМ для импульсного включения светодиода подсветки
hw_pwm_pin = 12
hw_pwm_freq = 25
hw_pwm_duty = 30000

hw_pwm_duty_step = 50000
hw_pwm_duty_min = 5000
hw_pwm_duty_max = 500000

min_mean_light_intensity = 165
max_mean_light_intensity = 180

# пин для ручного переключения клапана
manual_pin = 5

# назначение стартовых пинов клапанов №1-2-3
vent_pins = [22, 27, 17]

# пин бесперебойника
ups_pin = 4


def sleeper(seconds):
    def wrapped():
        print('Slept %s seconds' % seconds)
        time.sleep(seconds)

    return wrapped


# сколько раз повторить цикл (при работе из GUI интерфейса)
n_cycles = 45


class CycleType:
    VENTS = 0
    HYDRO = 1


CYCLE_TYPE = CycleType.VENTS


def get_cycle_vents(vents, capture):
    """
        Последовательность действий для одного цикла клапанной системы
        on\off - открытие\закрытие клапана № 1-3
        sleeper - ожидание в секундах
        capture - выполнение снимка. Занимает некоторое время (1-3 секунды)
        после каждой команды должна быть запятая.
        команды, закоментированные решеткой "#" не выполняются.
    """
    vent_1, vent_2, vent_3 = vents
    cycle_seq = [
        vent_1.off,
        sleeper(0.1),
        vent_2.off,
        sleeper(0.2),
        vent_3.off,
        sleeper(0.3),
        # ...
        vent_3.on,  # К1 открывается слив
        sleeper(1),
        vent_3.off,  # К1 закрывается слив
        sleeper(1),
        # ...
        vent_2.on,  # К2 открывается
        sleeper(2.0),
        vent_1.on,  # К3 открывается выход
        sleeper(2.0),
        vent_1.off,  # К3 закрывается выход
        sleeper(2.0),
        vent_2.off,  # К2 закрывается
        # ...
        sleeper(6.0),
        capture,
        sleeper(1)
    ]
    return cycle_seq


motor_pin = 17
sig_a_pin = 24
sig_b_pin = 14

# [сек] максимальное время поворота гидрораспределителя
HYDRO_TURN_TIMEOUT = 60


def get_cycle_hydro(controls, capture, wait_until):
    """
        Последовательность действий для одного цикла гидравлической системы.
        Система управляет вращением гидравлического цилиндра посредством моторчика.
        Сигналу Б соответствует вращение на 180 градусов относительно сигнала А,
        т.е. срабатывание обоих сигналов эквивалентно полному обороту.

        Рабочий цикл состоит из одного полного оборота и захвата снимка камерой.
        Для выполнения цикла включается моторчик и проверяется состояние контактов, присоединненных к сигналам А, Б.
        В исходной позиции, по-умолчанию активен сигнал А.
    """

    motor, sig_a, sig_b = controls
    cycle_seq = [
        motor.on(),
        wait_until(lambda: sig_a.is_pressed, HYDRO_TURN_TIMEOUT),
        wait_until(lambda: sig_b.is_pressed, HYDRO_TURN_TIMEOUT),
        motor.off(),
        capture,
    ]
    return cycle_seq
