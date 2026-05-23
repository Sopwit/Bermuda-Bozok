"""
Train XGBoost models for umbrella and clothing recommendations.

Reads hourly weather observations from ``data/hourly_observations.csv``,
trains two classifiers, and persists the artifacts to ``models/``.
"""

import json
import logging
import platform
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_class_weight

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"


def main() -> None:
    logger.info("Loading data...")
    df = pd.read_csv(DATA_DIR / "hourly_observations.csv")

    cols_to_drop = [
        "obs_id", "station_name", "station_id", "date", "timestamp",
        "recommendation_headline", "recommendation_text",
    ]
    df = df.drop(columns=cols_to_drop)

    logger.info("Processing categorical features...")
    cat_features = ["climate_zone", "season", "precipitation_type", "weather_condition", "road_surface"]
    df = pd.get_dummies(df, columns=cat_features, drop_first=True)

    y_umbrella = df["umbrella_needed"]

    le_clothing = LabelEncoder()
    y_clothing = le_clothing.fit_transform(df["clothing_recommendation"])

    X = df.drop(columns=["umbrella_needed", "clothing_recommendation", "outdoor_suitability_score"])

    X_train, X_test, y_train_umb, y_test_umb = train_test_split(
        X, y_umbrella, test_size=0.2, random_state=42,
    )
    _, _, y_train_cloth, y_test_cloth = train_test_split(
        X, y_clothing, test_size=0.2, random_state=42,
    )

    logger.info("Training umbrella model...")
    weight = len(y_train_umb[y_train_umb == 0]) / len(y_train_umb[y_train_umb == 1])
    model_umbrella = xgb.XGBClassifier(scale_pos_weight=weight, random_state=42, eval_metric="logloss")
    model_umbrella.fit(X_train, y_train_umb)

    logger.info("Training clothing model...")
    classes = np.unique(y_train_cloth)
    weights = compute_class_weight("balanced", classes=classes, y=y_train_cloth)
    weight_dict = dict(zip(classes, weights))
    sample_weights = np.array([weight_dict[y] for y in y_train_cloth])

    model_clothing = xgb.XGBClassifier(objective="multi:softprob", random_state=42)
    model_clothing.fit(X_train, y_train_cloth, sample_weight=sample_weights)

    logger.info("Saving models to disk...")
    joblib.dump(model_umbrella, MODELS_DIR / "model_umbrella.joblib")
    joblib.dump(model_clothing, MODELS_DIR / "model_clothing.joblib")
    joblib.dump(le_clothing, MODELS_DIR / "label_encoder_clothing.joblib")
    joblib.dump(list(X.columns), MODELS_DIR / "model_features.joblib")

    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "python_version": platform.python_version(),
        "package_versions": {
            "joblib": joblib.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit-learn": sklearn.__version__,
            "xgboost": xgb.__version__,
        },
        "artifacts": [
            "model_umbrella.joblib",
            "model_clothing.joblib",
            "label_encoder_clothing.joblib",
            "model_features.joblib",
        ],
    }
    with open(MODELS_DIR / "model_metadata.json", "w", encoding="utf-8") as fp:
        json.dump(metadata, fp, indent=2)

    logger.info("Done! Models are ready.")


if __name__ == "__main__":
    main()
