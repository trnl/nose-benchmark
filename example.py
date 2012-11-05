# -*- coding: utf-8 -*-
from benchmark import benchmark
import random
import time

class Test(object):
    @benchmark(threads=3, estimated_time=5)
    def testGenerateRandomNumber1(self):
        for i in range(self.iterations):
          time.sleep(1)            

    @benchmark(threads=5, estimated_time=2)
    def testGenerateRandomNumber2(self):
        for i in range(self.iterations):
            random.random()
