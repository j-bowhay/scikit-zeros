import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_equal

from scikit_poles_zeros._domain import Rectangle, _subdivide_domain

from . import problems


class TestRectangle:
    @pytest.mark.parametrize(("bl", "tr"), [(0, 0), (0, 1), (0, 1j), (1 + 1j, 0)])
    def test_iv(self, bl, tr):
        with pytest.raises(ValueError, match="right and above bottom left"):
            Rectangle(bl, tr)

    def test_attributes(self):
        bl, tr = 1 + 2j, 12 + 10j
        r = Rectangle(bl, tr)
        assert r.bottom_left == bl
        assert r.top_right == tr
        assert r.corners == (bl, 12 + 2j, tr, 1 + 10j)

    @pytest.mark.parametrize(
        "attr", ["top_right", "bottom_left", "children", "corners"]
    )
    def test_read_only(self, attr):
        d = Rectangle(0, complex(1, 1))
        with pytest.raises(AttributeError):
            setattr(d, attr, 1)

    @pytest.mark.parametrize("method", ["gk21", "tanhsinh"])
    @pytest.mark.parametrize(
        ("f", "bl", "tr", "expected"),
        [
            (lambda z: 1 / z, complex(-1, -1), complex(1, 1), 2j * np.pi),
            (lambda z: 1 / (z**2 + 1) ** 2, -1, complex(10, 10), np.pi / 2),
            (lambda z: np.sin(z), complex(-10, -10), complex(12, 3), 0),
        ],
    )
    def test_contour_integral(self, f, bl, tr, expected, method):
        d = Rectangle(bl, tr)
        res = d.contour_integral(f, method=method)
        assert_equal(res.success, np.ones_like(res.integral, dtype=np.bool))
        assert_equal(res.status, np.zeros_like(res.integral))
        assert_allclose(res.integral, expected, atol=1e-10)

    def test_contour_integral_args_pass_through(self):
        d = Rectangle(0, complex(1, 1))
        r = d.contour_integral(
            lambda z: z * 10, method="tanhsinh", quadrature_args={"maxlevel": 1}
        )
        assert np.all(~r.success)

    def test_contour_integral_invalid_method(self):
        d = Rectangle(0, complex(1, 1))
        with pytest.raises(ValueError, match="Invalid `method`"):
            d.contour_integral(lambda z: z, method="cheese")

    @pytest.mark.parametrize("problem", problems.all)
    @pytest.mark.parametrize("method", ["gk21", "tanhsinh"])
    def test_arg_principle(self, problem: problems.Problem, method):
        arg = {"maxlevel": 20} if method == "tanhsinh" else {}
        res = problem.domain.argument_principle(
            problem.f, problem.f_z, method=method, quadrature_args=arg
        )
        assert_allclose(
            res.integral,
            problem.expected_arg_principle(),
            atol=1e-12,
        )


class TestSubdivideDomain:
    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    @pytest.mark.parametrize(
        "f",
        [
            lambda z: z,
            lambda z: z - 0.5,
            lambda z: z - 1,
            lambda z: z - 0.5j,
            lambda z: z - 1j,
            lambda z: z - 1 - 1j,
        ],
    )
    def test_zero_on_boundary(self, f):
        r = Rectangle(0, complex(1, 1))
        with pytest.raises(RuntimeError, match="boundary"):
            _subdivide_domain(r, f, f_z=lambda _: 1.0, max_arg_principle=2)
