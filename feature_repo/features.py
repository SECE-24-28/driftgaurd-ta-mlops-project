"""
Feast Feature Definitions for DriftGuard.
Defines model features, entities, and sources for offline and online retrieval.
"""
from datetime import timedelta
from feast import (
    Entity,
    FeatureView,
    Field,
    FileSource,
)
from feast.types import Float32, String

# 1. Define Entity
prediction_entity = Entity(
    name="prediction_id",
    value_type=String,
    description="Unique identifier for model prediction logs",
)

# 2. Define Data Source
feature_source = FileSource(
    name="model_features_source",
    path="./data/features.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
)

# 3. Define Feature View
model_input_features = FeatureView(
    name="model_input_features",
    entities=[prediction_entity],
    ttl=timedelta(hours=1),
    schema=[
        Field(name="feature_0", dtype=Float32),
        Field(name="feature_1", dtype=Float32),
        Field(name="feature_2", dtype=Float32),
        Field(name="feature_3", dtype=Float32),
        Field(name="feature_4", dtype=Float32),
    ],
    online=True,
    source=feature_source,
    tags={"team": "driftguard_mlops"},
)
