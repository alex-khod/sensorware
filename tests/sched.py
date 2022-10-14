import sched
import time
import unittest
from unittest import mock


class TestSed(unittest.TestCase):

    def setUp(self):
        self.start_time = time.time()

        def delay(name):
            print("Waiting... %.2f" % (time.time() - self.start_time), name)
            time.sleep(0.5)

        def fake_delay():
            return mock.Mock(side_effect=delay)

        sed = sched.scheduler()
        sed.enter(delay=0, priority=1,
                  action=fake_delay(), argument=('first',))
        sed.enter(delay=1, priority=1, action=fake_delay(),
                  argument=('second',))
        sed.enter(delay=2, priority=1, action=fake_delay(),
                  argument=('third',))
        self.sed = sed

        self.m = mock.Mock()
        actions = [q.action for q in self.sed.queue]
        for act, i in zip(actions, 'abc'):
            self.m.attach_mock(act, i)

    def test_blocking_sed_call_order(self):
        self.sed.run()
        self.m()

        assert len(self.m.mock_calls) == 3 + 1
        # m.call is last
        assert self.m.mock_calls[-1] == mock.call()

    def test_nonblocking_sed_call_order(self):
        running = True
        while running:
            running = not self.sed.run(blocking=False) is None
            self.m()
            time.sleep(0.25)

        #  print(self.m.mock_calls)
        assert len(self.m.mock_calls) >= 3 + 1
        # m.call is called is called multiple times throughout the loop
        assert self.m.mock_calls[:2] == [mock.call.a('first'), mock.call()]


class TestExcSed(unittest.TestCase):

    def setUp(self):

        def delay_exception(name):
            raise Exception("Something is wrong")

        def fake_delay_exception():
            return mock.Mock(side_effect=delay_exception)

        sed = sched.scheduler()
        sed.enter(delay=0, priority=1,
                  action=fake_delay_exception(), argument=('exc first',))
        sed.enter(delay=0, priority=2, action=fake_delay_exception(),
                  argument=('post-exception of the event is skipped',))
        sed.enter(delay=0, priority=3, action=fake_delay_exception(),
                  argument=('exc second',))
        self.sed = sed

        self.m = mock.Mock()
        actions = [q.action for q in self.sed.queue]
        for act, i in zip(actions, 'abc'):
            self.m.attach_mock(act, i)

    def test_blocking_exc_sed_fails_on_exception(self):
        try:
            self.sed.run()
        except Exception:
            pass
        assert len(self.m.mock_calls) == 1

    def test_nonblocking_exc_sed_fails_on_exception(self):
        running = True
        try:
            while running:
                running = not self.sed.run(blocking=False) is None
            time.sleep(0.25)
        except Exception:
            pass
        assert len(self.m.mock_calls) == 1
