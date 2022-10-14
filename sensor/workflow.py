"""
    Module that implements main loop.
"""
import datetime
import os
import time
import traceback

from skimage import io

from sensor import utils, proxy, cycles, exc, capturing, leds
from sensor.canbus import app as can_app
from sensor.detector.sbd import SBDWrapper


class CycleProcessor:
    controls = None
    capture_func = None
    sequence = None
    image = None

    def process_cycle(self):
        for call in self.sequence:
            result = call()
            if hasattr(call, "is_capture"):
                self.image = result


class VentsCycleProcessor(CycleProcessor):
    def __init__(self, capture):
        self.capture_func = capture
        self.capture_func.is_capture = True
        self.controls = [leds.DigitalOutput(pin, 'K%d' % (i + 1), led_factory=proxy.gpio_led_factory) for i, pin in
                          enumerate(cycles.vent_pins)]
        self.sequence = cycles.get_cycle_vents(self.controls, self.capture_func)


class HydroCycleProcessor(CycleProcessor):
    def __init__(self, capture):
        self.capture_func = capture
        self.capture_func.is_capture = True
        motor = leds.DigitalOutput(cycles.motor_pin, 'Motor')
        sig_a = proxy.Button(cycles.sig_a_pin, 'Signal A')
        sig_b = proxy.Button(cycles.sig_b_pin, 'Signal B')
        self.controls = [motor, sig_a, sig_b]
        self.sequence = cycles.get_cycle_hydro(self.controls, self.capture_func, utils.wait_until)


class ImageCapture:
    """
        Use camera and CycleProcessor together to capture an image.
    """

    def __init__(self):
        self.camera = self.init_camera()
        # reserved
        self.vents_ok = True
        self.camera_ok = proxy.camera_ok

        search = capturing.IntensitySearch(self.camera)

        def capture():
            return search.capture()

        if cycles.CYCLE_TYPE == cycles.CycleType.VENTS:
            self.worker = VentsCycleProcessor(capture)
        else:
            self.worker = HydroCycleProcessor(capture)

    def init_camera(self):
        camera = proxy.camera
        camera.iso = 400
        camera.framerate = 20
        camera.resolution = (2592, 1952)
        camera.shutter_speed = 40000
        camera.color_effects = (128, 128)
        return camera

    def image_save_to(self, ext='jpg'):
        fmt = '%m-%d-%Y-%H=%M=%S_%f.' + ext
        time_stamp = datetime.datetime.now().strftime(fmt)
        path = os.path.join(utils.Pathing.image_dir, time_stamp)
        return utils.Pathing.image_dir, path

    def try_capture(self, force):
        try:
            if force:
                self.worker.capture_func()
                time.sleep(1)
            else:
                self.worker.process_cycle()
        except (exc.ExceptionBadDuty, exc.ExceptionDutyUpperLimitReached, exc.ExceptionDutyUpperLimitReached) as e:
            print("Failed to adjust brightness: ", e.__class__.__name__)

    def process_capture(self, force):
        self.try_capture(force)
        image = self.worker.image
        self.worker.image = None
        if image is None:
            return None, None
        _, path = self.image_save_to()
        imagedef = (image, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        free_space_mb = utils.get_free_space('.')
        if free_space_mb > 4096:
            io.imsave(path, image)
        return imagedef


class DetectorWrapper:
    """
        Feed image onto the detector and process / calculate / write results.
    """

    SNAPSHOT_CYCLE_PERIOD = 50

    def __init__(self):
        self.detector = SBDWrapper()
        self.writer = DataWriter()

        self.image_idx = 1
        self.n_particles = 0
        self.mean_diam = 0
        self.d_param = 0
        self.dt_param = 0

        self.d_params = []
        self.d_params_old = []

    def process(self, imagedef):
        print("Executing cycle №%d" % (self.image_idx + 1))
        image, path = imagedef
        if image is None:
            return
        keys, _ = self.detector.process_dynamic_mask(imagedef)
        mean_diam = 0
        n_particles = 0
        d_param = 0
        if keys is not None and keys.any():
            diams = keys[:, 2]
            mean_diam = diams.mean()
            n_particles = len(keys)
            d_param = (diams ** 3).sum() / 1e6
            self.writer.write_detection_diams(self.image_idx, diams)
            results_summary = (self.image_idx, path, n_particles, mean_diam, cycles.hw_pwm_duty, d_param)
            self.writer.write_detection_results(results_summary)
        if n_particles > 0:
            print('%d particles detected with mean diam %.3f' % (n_particles, mean_diam))
        self.mean_diam = mean_diam
        self.n_particles = n_particles
        self.d_param = d_param
        self.d_params.append(d_param)
        self.update_batch_data()
        self.image_idx += 1

    def update_batch_data(self):
        if len(self.d_params) >= self.SNAPSHOT_CYCLE_PERIOD:
            d1 = sum(self.d_params)
            if self.d_params_old:
                d0 = sum(self.d_params_old)
                self.dt_param = (d1 - d0) / d0 if d0 != 0 else 0
            self.d_params_old = self.d_params
            self.d_params = []
            self.writer.write_d_param_sum(self.image_idx, d1)


class DataWriter:
    def __init__(self):
        db_dir = utils.Pathing.get_new_db_dir(utils.Pathing.db_root)
        self.param_db = os.path.join(db_dir, "loads.db")
        self.diams_db = os.path.join(db_dir, "data.db")
        self.snaps_db = os.path.join(db_dir, "snaps.db")

    def write_d_param_sum(self, idx, d_param_sum):
        with open(self.param_db, 'a') as f:
            f.write('%d;%f\n' % (idx, d_param_sum))

    def write_detection_diams(self, idx, path, diams):
        with open(self.diams_db, 'a') as f:
            for diam in diams:
                f.write('%d;%s;%s\n' % (idx, path, diam))

    def write_detection_results(self, results):
        with open(self.snaps_db, 'a') as f:
            f.write('%d;%s;%d;%f;%d;%f\n' % results)


class WorkController:

    def __init__(self, run_can=True):
        # self.ups = proxy.Button(cycles.ups_pin, pull_up=None, active_state=True)

        self.can_app = None
        if run_can:
            self.can_app = can_app.init_app()
        self.image_capture = ImageCapture()
        self.detector_wrapper = DetectorWrapper()

    def check_ups(self):
        raise NotImplementedError
        # power = self.ups.is_pressed
        # if power:
        #     print("Power HIGH")
        # else:
        #     print("Power LOW")

    def update_canbus_state(self):
        data = {
            'ready': 0,
            'param_1': self.detector_wrapper.d_param,
            'param_2': self.detector_wrapper.dt_param,
            'n_particles': self.detector_wrapper.n_particles,
            'camera_ok': self.image_capture.camera_ok,
            'vents_ok': self.image_capture.vents_ok
        }
        self.can_app.state_handler.set_data(data)
        free_space_mb = utils.get_free_space('.')
        progress_item = [self.detector_wrapper.image_idx,
                         self.can_app.state_handler.allow_capture,
                         self.image_capture.camera_ok,
                         self.image_capture.vents_ok,
                         self.detector_wrapper.n_particles,
                         cycles.hw_pwm_duty,
                         self.detector_wrapper.d_param,
                         self.detector_wrapper.dt_param,
                         free_space_mb]
        self.can_app.state_handler.add_queue_item(progress_item)

    def work_loop(self):
        os.makedirs(utils.Pathing.db_root, exist_ok=True)
        while True:
            if self.can_app.shutdown_handler.shutting_down:
                break
            try:
                self.do_work_loop()
            except Exception:
                print("Unhandled exception at work loop")
                traceback.print_exc()
        if self.can_app:
            self.can_app.ready_for_shutdown = True
        while True:
            time.sleep(0.25)

    def do_work_loop(self):
        allow_capture = self.can_app.state_handler.allow_capture
        self.update_canbus_state()
        force = (allow_capture == self.can_app.FORCE_CAPTURE)
        should_work = (allow_capture and self.image_capture.camera_ok) or force
        imagedef = self.image_capture.process_capture(force)

        if not should_work:
            print("Can't work, idling")
            time.sleep(3)
            return

        self.detector_wrapper.process(imagedef)


def run():
    cnt = WorkController()
    cnt.work_loop()


if __name__ == "__main__":
    run()
