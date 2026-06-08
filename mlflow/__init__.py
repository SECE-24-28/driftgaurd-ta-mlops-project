"""Minimal local MLflow stub for offline testing."""
from contextlib import contextmanager

_tracking_uri = None
_experiment_name = None


def set_tracking_uri(uri):
    global _tracking_uri
    _tracking_uri = uri


def set_experiment(name):
    global _experiment_name
    _experiment_name = name


@contextmanager
def start_run(run_name=None):
    yield object()


def log_params(params):
    return None


def log_metrics(metrics):
    return None


def log_artifact(path):
    return None


from . import sklearn  # noqa: E402,F401
from . import tracking  # noqa: E402,F401
