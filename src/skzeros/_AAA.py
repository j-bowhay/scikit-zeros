import numpy as np
import scipy

__all__ = ["AAA", "evaluate", "poles_residues", "zeros"]


def AAA(f, r, *, rtol=1e-13, max_iter=100, err_on_max_iter=True, initial_samples=16):
    # Initial support points
    t = np.array([])
    S = np.array([])
    while (m := S.size) < max_iter:
        tm = _XS(t, max(3, initial_samples - m))
        X = r.sample_boundary(tm)
        fX = f(X)
        to_keep = (np.isfinite(fX)) & (~np.isnan(fX))
        X = X[to_keep]
        fX = fX[to_keep]
        fS = f(S)

        if m == 0:
            R = np.mean(fX)
        else:
            C = 1 / np.subtract.outer(X, S)
            A = np.subtract.outer(fX, fS) * C
            _, _, V = scipy.linalg.svd(
                A, full_matrices=(A.shape[0] <= A.shape[1]), check_finite=False
            )
            w = V.conj()[-1, :]
            R = (C @ (w * fS)) / (C @ w)

        err = np.linalg.norm(fX - R, ord=np.inf)
        fmax = np.linalg.norm(np.concat((fS, fX)), ord=np.inf)
        if err < rtol * fmax:
            return S, fS, w

        j = np.argmax(np.abs(fX - R))
        t = np.append(t, tm[j])
        S = np.append(S, X[j])
    if err_on_max_iter:
        msg = f"Iteration limit reached, current error {err}, require err {rtol * fmax}"
        raise RuntimeError(msg)
    return S[:-1], fS, w


def _XS(S, p):
    # make sure the end points 0 and 1 are included so we sample to the left of the
    # first support point and to the right of the last support point
    if 0 not in S:
        S = np.append(S, 0)
    if 1 not in S:
        S = np.append(S, 1)
    S = np.sort(S)
    d = np.arange(1, p + 1) / (p + 1)
    return (S[:-1] + np.multiply.outer(d, np.diff(S))).ravel()


def poles_residues(z, f, w, residue=False):
    # poles
    m = w.size
    B = np.eye(m + 1, dtype=w.dtype)
    B[0, 0] = 0

    E = np.zeros_like(B, dtype=np.result_type(w, z))
    E[0, 1:] = w
    E[1:, 0] = 1
    np.fill_diagonal(E[1:, 1:], z)

    pol = scipy.linalg.eigvals(E, B)
    poles = pol[np.isfinite(pol)]

    if residue:
        # residue
        with np.errstate(divide="ignore", invalid="ignore"):
            N = (1 / (np.subtract.outer(poles, z))) @ (f * w)
            Ddiff = -((1 / np.subtract.outer(poles, z)) ** 2) @ w
            return poles, N / Ddiff
    return poles


def zeros(z, f, w):
    # zeros
    m = w.size
    B = np.eye(m + 1, dtype=w.dtype)
    B[0, 0] = 0

    E = np.zeros_like(B, dtype=np.result_type(w, z, f))
    E[0, 1:] = w * f
    E[1:, 0] = 1
    np.fill_diagonal(E[1:, 1:], z)

    zeros = scipy.linalg.eigvals(E, B)
    return zeros[np.isfinite(zeros)]


def evaluate(z, f, w, Z):
    # evaluate rational function in barycentric form.
    Z = np.asarray(Z)
    zv = np.ravel(Z)

    weights = w[..., np.newaxis]

    # Cauchy matrix
    # Ignore errors due to inf/inf at support points, these will be fixed later
    with np.errstate(invalid="ignore", divide="ignore"):
        CC = 1 / np.subtract.outer(zv, z)
        # Vector of values
        r = CC @ (weights * f) / (CC @ weights)

    # Deal with input inf: `r(inf) = lim r(z) = sum(w*f) / sum(w)`
    if np.any(np.isinf(zv)):
        r[np.isinf(zv)] = np.sum(weights * f) / np.sum(weights)

    # Deal with NaN
    ii = np.nonzero(np.isnan(r))[0]
    for jj in ii:
        if np.isnan(zv[jj]) or not np.any(zv[jj] == z):
            # r(NaN) = NaN is fine.
            # The second case may happen if `r(zv[ii]) = 0/0` at some point.
            pass
        else:
            # Clean up values `NaN = inf/inf` at support points.
            # Find the corresponding node and set entry to correct value:
            r[jj] = f[zv[jj] == z].squeeze()

    return np.reshape(r, Z.shape)
