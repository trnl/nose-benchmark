import sys, os, logging, math, time, resource

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

def info(title):
    log.debug('Test name:' + title)
    log.debug('Parent process:' + str(os.getppid()))
    log.debug('Process id:' + str(os.getpid()))


def invoker(object, fname):
    info(fname)
    rusage_mode = resource.RUSAGE_CHILDREN
    rusage_before = resource.getrusage(rusage_mode)
    real_before = time.time()
    
    # actual run
    getattr(object,fname)._wrapped(object)

    rusage_after = resource.getrusage(rusage_mode)
    real_after = time.time()
    
    fields = filter(lambda item: item.startswith('ru_'), dir(rusage_after))
    x = dict([(field, getattr(rusage_after, field)-getattr(rusage_before, field)) for field in fields])
    x['ru_rtime'] = real_after - real_before
    return x     
    
def estimate_iterations(fn, object, estimated_time):
    object.iterations=1
    rusage = invoker(object,fn.__name__)
    attempts = 0;
    while rusage['ru_rtime'] < estimated_time and attempts < 10:
        attempts += 1
        object.iterations *= int(math.ceil(estimated_time / rusage['ru_rtime'])) 
        log.debug("t: %f, i:%d" % (rusage['ru_rtime'], object.iterations))
        rusage = invoker(object,fn.__name__)
    log.info("Estimated iterations: %d" % object.iterations)
    

def benchmark(rounds=5, warmupRounds=2, threads=1, estimated_time=5):
    """
    Decorator, that marks test to be executed 'rounds'
    times using number of threads specified in 'threads'.
    """
    def decorator(fn):
        global measurements
        ruMeasurements = []
        oneTestMeasurements = {}

        def wrapper(self, *args, **kwargs):
            className = self.__class__.__name__
            methodName = fn.__name__
            
            # here will be self-calibration
            estimate_iterations(fn,self,estimated_time)
            
            promises = []
            
            pool = Pool(threads)
            for i in range(warmupRounds+rounds):
                result = pool.apply_async(invoker, args=(self, fn.__name__))
                if (i > warmupRounds):
                    promises.append(result)

            pool.close()
            pool.join()

            for promise in promises:
                # Get the measurements returned by invoker function
                ruMeasurements.append(promise.get())

            oneTestMeasurements['title'] = methodName
            oneTestMeasurements['class'] = className
            oneTestMeasurements['results'] = ruMeasurements
            oneTestMeasurements['iterations'] = self.iterations            

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
            rounds = len(measurements[i]['results'])
            iterations = measurements[i]['iterations']
            
            averages = {}
            for field in measurements[i]['results'][0]:
              averages[field] = sum([x[field] for x in measurements[i]['results']]) / rounds
            
            performanceResult = dict(averages)
            performanceResult['title'] = measurements[i]['title']
            performanceResult['class'] = measurements[i]['class']
            performanceResult['rounds'] = rounds
            performanceResult['iterations'] = iterations            
            performanceResult['timeReal'] = averages['ru_rtime']
            performanceResult['timeUser'] = averages['ru_utime']
            if performanceResult['timeReal'] > 0:
                performanceResult['opsReal'] = iterations / performanceResult['timeReal']
            else:
                performanceResult['opsReal'] = 0
            
            if performanceResult['timeUser'] > 0:
                performanceResult['opsUser'] = iterations / performanceResult['timeUser']
            else:
                performanceResult['opsUser'] = 0

            performanceResults.append(performanceResult)

        # Clear measurements for next module
        del measurements[:]

        if hasattr(object, '__module__'):
            resultsToSave = json.dumps(performanceResults, indent=4)
            log.debug(resultsToSave)

            dir = 'reports/'

            if not os.path.exists(dir):
                os.makedirs(dir)

            # Save the results
            f = open(dir + object.__module__ + '.json', 'w')
            f.write(resultsToSave)            

