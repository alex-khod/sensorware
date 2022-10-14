import time
import os

while True:
    for i in range(10):
        with open(os.path.join('.', 'testlog.txt'), 'a') as f:
            f.write('testing %d...' % i)
        time.sleep(1.0)
    raise(Exception('Not implemented'))