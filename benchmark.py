import sys, os, logging, math, time

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

from nose.plugins import Plugin

from multiprocessing import Pool

import re

def upper(matchobj):
    return matchobj.group(0).upper()


def scoreatpercentile(N, percent, key=lambda x:x):
    """
    Find the percentile of a list of values.

    @parameter N - is a list of values. Note N MUST BE already sorted.
    @parameter percent - a float value from 0.0 to 1.0.
    @parameter key - optional key function to compute value from each element of N.

    @return - the percentile of the values
    """
    if not N:
        return None
    k = (len(N)-1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return key(N[int(k)])
    d0 = key(N[int(f)]) * (c-k)
    d1 = key(N[int(c)]) * (k-f)
    return d0+d1


log = logging.getLogger('nose.plugins.benchmark')

measurements = []
resArray = []

def info(title):
    log.debug('Test name:' + title)
    log.debug('Parent process:' + str(os.getppid()))
    log.debug('Process id:' + str(os.getpid()))


def invoker(object, fname, repeats):
    info(fname)
    # TODO:
    # Counting only CPU time now
    tstart = time.clock()

    for i in range(repeats):
        getattr(object,fname)._wrapped(object)

    tend = time.clock()

    return tend - tstart

def benchmark(invocations=1, repeats=1, threads=1):
    """
    Decorator, that marks test to be executed 'invocations'
    times using number of threads specified in 'threads'.
    """
    def decorator(fn):
        global measurements, resArray
        resArray = []
        timesMeasurements = []
        oneTestMeasurements = {}

        def wrapper(self, *args, **kwargs):
            className = self.__class__.__name__
            methodName = fn.__name__
          
            pool = Pool(threads)
            for i in range(invocations):
                res = pool.apply_async(invoker, args=(self, fn.__name__, repeats))
                # Gather res links
                resArray.append(res)

            pool.close()
            pool.join()

            for res in resArray:
                # Get the measurements returned by invoker function
                timesMeasurements.append(res.get())

            oneTestMeasurements['title'] = methodName
            oneTestMeasurements['class'] = className
            oneTestMeasurements['results'] = timesMeasurements
            oneTestMeasurements['invocations'] = invocations
            oneTestMeasurements['repeats'] = repeats

            measurements.append(oneTestMeasurements)

        wrapper.__doc__ = fn.__doc__
        wrapper.__name__ = fn.__name__
        wrapper._wrapped = fn
        return wrapper
    return decorator


class Benchmark(Plugin):
    name = 'benchmark'

    def options(self, parser, env=os.environ):
        super(Benchmark, self).options(parser, env=env)     

    def configure(self, options, conf):
        super(Benchmark, self).configure(options, conf)

        if not self.enabled:
            return

    def stopContext(self, object):
        """
        Count and export performance results to JSON file
        """
        performanceResults = []

        for i in range(len(measurements)):
            performanceResult = {}
            performanceResult['title'] = measurements[i]['title']
            performanceResult['class'] = measurements[i]['class']
            performanceResult['invocations'] = measurements[i]['invocations']
            performanceResult['repeats'] = measurements[i]['repeats']
            performanceResult['executionTime'] = sum(measurements[i]['results'])
            performanceResult['invocations'] = len(measurements[i]['results'])
            performanceResult['min'] = min(measurements[i]['results'])
            performanceResult['max'] = max(measurements[i]['results'])
            performanceResult['average'] = sum(measurements[i]['results']) / len(measurements[i]['results'])
            performanceResult['median'] = scoreatpercentile(sorted(measurements[i]['results']), 0.5)
            performanceResult['90percentile'] = scoreatpercentile(sorted(measurements[i]['results']), 0.9)

            if performanceResult['average']>0:
                performanceResult['operationsPerSecond'] = measurements[i]['repeats']/performanceResult['average']

            performanceResults.append(performanceResult)

        # Clear measurements for next module
        del measurements[:]

        if hasattr(object, '__module__'):
            resultsToSave = json.dumps(performanceResults, indent=4)
            log.debug(resultsToSave)

            # Form results to post
            performanceResultsPost = []

            # Adapt names
            testRemoveReg = re.compile(re.escape('test'), re.IGNORECASE)

            for performanceResult in performanceResults:
                tmpResult = {}
                tmpResult['name'] = testRemoveReg.sub('', performanceResult['title']).upper()
                tmpResult['class'] = testRemoveReg.sub('', performanceResult['class'])
                tmpResult['label'] = 'Python ' + str(sys.version_info[0]) + '.' + str(sys.version_info[1]) + '.' + str(sys.version_info[2])
                tmpResult['time'] = int(time.time())

                tmpResult['report'] = {}
                tmpResult['report'] = performanceResult

                performanceResultsPost.append(tmpResult)

            # TODO:
            # Get path from params
            dir = 'reports/'

            if not os.path.exists(dir):
                os.makedirs(dir)

            # Save the results
            f = open(dir + object.__module__ + '.json', 'w')
            f.write(resultsToSave)            

