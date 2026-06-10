"""
DriftGuard package setup configuration.
"""
from setuptools import setup, find_packages

setup(
    name="driftguard",
    version="1.0.0",
    description="DriftGuard — Autonomous Model Health Platform",
    author="DriftGuard Team",
    packages=find_packages(
        include=[
            "driftguard",
            "driftguard.*",
        ]
    ),
    install_requires=[
        # SDK client — what sdk/tracker.py, drift_detector.py, config.py actually import
        "numpy>=1.24",
        "httpx>=0.24",
        "python-dotenv>=1.0",
        "river>=0.21.2",
        "scikit-learn>=1.3",
    ],
    extras_require={
        "server": [
            # API server deps — only needed when running main.py
            "fastapi==0.111.0",
            "uvicorn==0.28.1",
            "pydantic==1.10.13",
            "prometheus-client==0.20.0",
            "pandas==2.2.2",
            "redis==5.0.4",
            "psycopg2-binary==2.9.9",
            "sqlalchemy==2.0.30",
        ],
        "validation": [
            "great-expectations==0.18.15",
            "sqlalchemy==1.4.41",
        ],
        "evidently": [
            "evidently==0.4.30",
        ],
        "serving": [
            "bentoml==1.2.0",
            "ray[serve]==2.10.0",
        ],
        "pipeline": [
            "prefect==2.19.0",
            "zenml==0.57.0",
        ],
        "test": [
            "pytest==8.2.0",
            "pytest-asyncio==0.23.6",
        ]
    },
    python_requires=">=3.9",
)
