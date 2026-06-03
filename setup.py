"""
DriftGuard package setup configuration.
"""
from setuptools import setup, find_packages

setup(
    name="driftguard",
    version="1.0.0",
    description="DriftGuard — Autonomous Model Health Platform",
    author="DriftGuard Team",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.111.0",
        "uvicorn==0.29.0",
        "pydantic==2.7.0",
        "river==0.21.0",
        "mlflow==2.13.0",
        "wandb==0.17.0",
        "prometheus-client==0.20.0",
        "scikit-learn==1.4.2",
        "pandas==2.2.2",
        "numpy==1.26.4",
        "python-dotenv==1.0.1",
        "httpx==0.27.0",
        "reportlab==4.1.0",
        "redis==5.0.4",
    ],
    extras_require={
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
    python_requires=">=3.11, <3.12",
)
