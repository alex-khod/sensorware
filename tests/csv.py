import csv
import os
import unittest


class TestLoadWrite(unittest.TestCase):
    def test_write_read(self):
        thing = ['hello', 800, 600]
        things = [thing, thing]

        fn = os.path.join("data", "test.csv")

        os.makedirs(os.path.dirname(fn), exist_ok=True)

        csv_args = {
            'delimiter': ';',
            # 'quotechar' : '\"',
            'quoting': csv.QUOTE_NONNUMERIC
        }

        if os.path.isfile(fn):
            os.remove(fn)

        with open(fn, 'a', newline='') as f:
            w = csv.writer(f, **csv_args)
            w.writerows(things)

        with open(fn, 'r') as f:
            r = csv.reader(f, **csv_args)
            _things = list(r)
            assert _things == things
