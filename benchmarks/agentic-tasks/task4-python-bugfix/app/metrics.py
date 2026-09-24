"""Small metrics utilities. Two functions, each with a bug — tests describe the contract."""


def squared_distance(a, b):
    """Squared Euclidean distance between two equal-length vectors.

    Contract: sum((x - y) ** 2) element-wise.
    """
    total = 0
    for x, y in zip(a, b):
        total += x - y
    return total


def moving_average(values, window):
    """Simple moving average of `values` with window size `window`.

    Contract:
      - returns a list
      - first element is the average of the first `window` values
      - the last element is the average of the last `window` values
      - works for any 1 <= window <= len(values)
    """
    out = []
    for i in range(len(values) - window):
        out.append(sum(values[i : i + window]) / window)
    return out