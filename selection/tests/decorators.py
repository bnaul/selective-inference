def set_sampling_params_iftrue(test_params, nsim=10, burnin=10, ndraw=10):
    def param_decorator(func):
        if test_params:
            def new_func(*args, **kwargs):
                kwargs['nsim'] = nsim
                kwargs['burnin'] = burnin
                kwargs['ndraw'] = ndraw
                return func(*args, **kwargs)
            return new_func
        else:
            return func
    return param_decorator


def set_seed_for_test(seed=None):
    def seed_decorator(func):
        import numpy as np
        np.random.seed(seed)
        return func
    return seed_decorator
