"""
DriftGuard package setup configuration.
"""

from pathlib import Path
from setuptools import setup, find_packages

# Read README.md for PyPI long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="driftguard-ai-sdk",
    version="1.0.2",  # Increment version before uploading
    description="Production-grade AI model monitoring, drift detection, and autonomous retraining platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="DriftGuard Team",
    packages=find_packages(
        include=[
            "driftguard",
            "driftguard.*",
        ]
    ),
    install_requires=[
        "numpy>=1.24",
        "httpx>=0.24",
        "python-dotenv>=1.0",
        "river>=0.21.2",
        "scikit-learn>=1.3",
    ],
    extras_require={
        "server": [
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
        ],
    },
    python_requires=">=3.9",
    keywords=[
        "mlops",
        "machine-learning",
        "drift-detection",
        "model-monitoring",
        "ai",
        "observability",
        "retraining",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries",
    ],
)