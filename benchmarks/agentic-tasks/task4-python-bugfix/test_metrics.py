import math

import pytest

from app.metrics import moving_average, squared_distance


def test_squared_distance_basic():
    assert squared_distance([1, 0], [0, 1]) == 2
    assert squared_distance([3, 5], [1, 2]) == 13


def test_squared_distance_zero():
    assert squared_distance([4, 4], [4, 4]) == 0


def test_squared_distance_floats():
    assert math.isclose(squared_distance([0.5], [0.25]), 0.0625)


def test_moving_average_full_window():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


def test_moving_average_equal_to_len():
    assert moving_average([2, 4, 6], 3) == [4.0]


def test_moving_average_window_one():
    assert moving_average([5, 5], 1) == [5.0, 5.0]