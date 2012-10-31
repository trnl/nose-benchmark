# -*- coding: utf-8 -*-
from benchmark import benchmark
import random

class Test(object):
    @benchmark(threads=3)
    def testGenerateRandomNumber1(self):
        for i in range(999999):
            random.random()

    @benchmark(threads=5)
    def testGenerateRandomNumber2(self):
        for i in range(999999):
            random.random()
