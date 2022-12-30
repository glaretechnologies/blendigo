class MetaSimpleProfiler(type):
    def __str__(cls):
        return cls._print(cls.all_time)

class SimpleProfiler(metaclass=MetaSimpleProfiler):
    from time import perf_counter_ns
    all_time = 0
    begin_time = 0
    
    # Disabled by default
    enabled = False

    @classmethod
    def enable(cls, state:bool=True):
        cls.enabled = state
    
    @classmethod
    def reset(cls):
        cls.all_time = 0
    
    @staticmethod
    def sum_time(func):
        if not SimpleProfiler.enabled:
            return func

        def wrap(*args, **kwargs):
            SimpleProfiler.begin_time = SimpleProfiler.perf_counter_ns()
            res = func(*args, **kwargs)
            SimpleProfiler.all_time += SimpleProfiler.perf_counter_ns() - SimpleProfiler.begin_time
            return res
        return wrap
    
    @staticmethod
    def _print(all_time):
        return f"{all_time/10**6:.3f} ms, {all_time / 16666666 * 100:.1f}% frame"

    @staticmethod
    def measure_this(name):
        def func_wrap(func):
            def args_wrap(*args, **kwargs):
                if not SimpleProfiler.enabled:
                    return func(*args, **kwargs)

                begin_time = SimpleProfiler.perf_counter_ns()
                res = func(*args, **kwargs)
                all_time = SimpleProfiler.perf_counter_ns() - begin_time
                print(f"Timer '{name}':", SimpleProfiler._print(all_time))
                return res
            return args_wrap
        return func_wrap

if __name__ == "__main__":
    from timeit import timeit
    print('Function:', timeit(setup='def a():return', stmt='a()'))

    setup='''
@SimpleProfiler.sum_time
def a(): return
'''
    print('Overhead disabled:', timeit(setup=setup, stmt='a()', globals=globals()))
    setup='''
SimpleProfiler.enable()
@SimpleProfiler.sum_time
def a(): return
'''
    print('Overhead enabled:', timeit(setup=setup, stmt='a()', globals=globals()))

    setup='''
SimpleProfiler.enable(False)
@SimpleProfiler.measure_this('disabled')
def a(): return
'''
    print('Measure Overhead disabled:', timeit(setup=setup, stmt='a()', globals=globals()))
    setup='''
SimpleProfiler.enable()
@SimpleProfiler.measure_this('enabled')
def a(): return
'''
    print('Measure Overhead enabled 10x:', timeit(number=10, setup=setup, stmt='a()', globals=globals()))