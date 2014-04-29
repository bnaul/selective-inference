"""
This module includes `covtest`_ that computes
either the exponential approximation from `covTest`_
the exact form of the covariance test described in 
`Spacings`_.

The covariance test itself is asymptotically exponential
(under certain conditions) and is  described in 
`covTest`_. 

Both tests mentioned above require knowledge 
(or a good estimate) of sigma, the noise variance.

This module also includes a second exact test called `reduced_covtest`_
that can use sigma but does not need it.

.. _covTest: http://arxiv.org/abs/1301.7161
.. _Kac Rice: http://arxiv.org/abs/1308.3020
.. _Spacings: http://arxiv.org/abs/1401.3889
.. _post selection LASSO: http://arxiv.org/abs/1311.6238

"""

import numpy as np
from .affine import constraints, simulate_from_constraints, gibbs_test
from .forward_step import forward_stepwise

def covtest(X, Y, sigma=1, exact=True,
            covariance=None):
    """
    The exact and approximate
    form of the covariance test, described
    in the `covTest`_, `Kac Rice`_ and `Spacings`_ papers.

    .. _covTest: http://arxiv.org/abs/1301.7161
    .. _Kac Rice: http://arxiv.org/abs/1308.3020
    .. _Spacings: http://arxiv.org/abs/1401.3889

    Parameters
    ----------

    X : np.float((n,p))

    Y : np.float(n)

    sigma : float (optional)
        Defaults to 1, but Type I error will be off if incorrect
        sigma is used.

    exact : bool (optional)
        If True, use the first spacings test, else use
        the exponential approximation.

    Returns
    -------

    con : `selection.affine.constraints`_
        The constraint based on conditioning
        on the sign and location of the maximizer.

    pvalue : float
        Exact or approximate covariance test p-value.

    idx : int
        Variable achieving $\lambda_1$

    sign : int
        Sign of $X^Ty$ for variable achieving $\lambda_1$.

    """
    n, p = X.shape

    Z = np.dot(X.T, Y)
    idx = np.argsort(np.fabs(Z))[-1]
    sign = np.sign(Z[idx])

    I = np.identity(p)
    subset = np.ones(p, np.bool)
    subset[idx] = 0
    selector = np.vstack([X.T[subset],-X.T[subset],-sign*X[:,idx]])
    selector -= (sign * X[:,idx])[None,:]

    con = constraints(selector, np.zeros(selector.shape[0]),
                      covariance=covariance)
    con.covariance *= sigma**2
    if exact:
        return con, con.pivot(X[:,idx] * sign, Y, alternative='greater'), idx, sign
    else:
        L2, L1, _, S = con.bounds(X[:,idx] * sign, Y)
        exp_pvalue = np.exp(-L1 * (L1-L2) / S**2) # upper bound is ignored
        return con, exp_pvalue, idx, sign

def reduced_covtest(X, Y, ndraw=5000, burnin=2000, sigma=None,
                    covariance=None):
    """
    An exact test that is more
    powerful than `covtest`_ but that requires
    sampling for the null distribution.

    This test does not require knowledge of sigma.
    
    .. _covTest: http://arxiv.org/abs/1301.7161
    .. _Kac Rice: http://arxiv.org/abs/1308.3020
    .. _Spacings: http://arxiv.org/abs/1401.3889

    Parameters
    ----------

    X : np.float((n,p))

    Y : np.float(n)

    burnin : int
        How many iterations until we start
        recording samples?

    ndraw : int
        How many samples should we return?

    sigma : float (optional)
        If provided, this value is used for the
        Gibbs sampler.

    covariance : np.float (optional)
        Optional covariance for cone constraint.
        Will be scaled by sigma if it is not None.

    Returns
    -------

    con : `selection.affine.constraints`_
        The constraint based on conditioning
        on the sign and location of the maximizer.

    pvalue : float
        Exact p-value.

    idx : int
        Variable achieving $\lambda_1$

    sign : int
        Sign of $X^Ty$ for variable achieving $\lambda_1$.


    """

    cone, _, idx, sign = covtest(X, Y, sigma=sigma or 1,
                                 covariance=covariance)

    pvalue = gibbs_test(cone, Y, X[:,idx] * sign,
                        ndraw=ndraw,
                        burnin=burnin,
                        sigma_known=sigma is not None)

#     if sigma is not None:
#         cone.covariance /= sigma**2
#         cone.linear_part /= sigma
#         cone.offset /= sigma

#     Z = simulate_from_sphere(cone,
#                              Y,
#                              ndraw=ndraw,
#                              burnin=burnin,
#                              white=(covariance is None) and (sigma is None))
#     if sigma is None:
#         norm_Y = np.linalg.norm(Y)
#         Z /= np.sqrt((Z**2).sum(1))[:,None]
#         Z *= norm_Y
#     else:
#         Z *= sigma

#     test_statistic = np.dot(Z, 
#     observed = np.fabs(np.dot(X.T,Y)).max()
#     pvalue = (test_statistic >= observed).mean()

    return cone, pvalue, idx, sign

def forward_step(X, Y, sigma=None,
                 nstep=5,
                 exact=False,
                 burnin=1000,
                 ndraw=5000):
    """
    A simple implementation of forward stepwise
    that uses the `reduced_covtest` iteratively
    after adjusting fully for the selected variable.

    This implementation is not efficient, in
    that it computes more SVDs than it really has to.

    Parameters
    ----------

    X : np.float((n,p))

    Y : np.float(n)

    sigma : float (optional) 
        Noise level (not needed for reduced).

    nstep : int
        How many steps of forward stepwise?

    exact : bool
        Which version of covtest should we use?

    burnin : int
        How many iterations until we start
        recording samples?

    ndraw : int
        How many samples should we return?

    tests : ['reduced_known', 'covtest', 'reduced_unknown']
        Which test to use? A subset of the above sequence.

    """

    n, p = X.shape
    FS = forward_stepwise(X, Y)

    covtest_P = []
    reduced_P = []
    for i in range(nstep):
        FS.next()

        # covtest
        if FS.P[i] is not None:
            RX = X - FS.P[i](X)
            RY = Y - FS.P[i](Y)
            covariance = np.identity(n) - np.dot(FS.P[i].U, FS.P[i].U.T)
        else:
            RX = X
            RY = Y
            covariance = None
        RX -= RX.mean(0)[None,:]
        RX /= RX.std(0)[None,:]

        con, pval, idx, sign = covtest(RX, RY, sigma=sigma,
                                       covariance=covariance,
                                       exact=exact)
        covtest_P.append(pval)

        # reduced

        eta = RX[:,idx] * sign
        Acon = constraints(FS.A, np.zeros(FS.A.shape[0]))
        if i > 0:
            U = FS.P[-2].U.T
            Uy = np.dot(U, Y)
            Acon = Acon.conditional(U, Uy)
        else:
            Acon = Acon
        Acon.covariance *= sigma**2

        Z = simulate_from_constraints(Acon,
                                      Y,
                                      ndraw=ndraw,
                                      burnin=burnin)
        observed = (eta * Y).sum()
        reduced_pval = (np.dot(Z, eta) >= observed).mean()
        reduced_P.append(reduced_pval)

    return covtest_P, reduced_P