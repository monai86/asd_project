import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from pathlib import Path

csv_path = Path("data/combined_features.csv")
if csv_path.exists():
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["group"])
    
    features = [
        "age_months", "total_utterances", "mlu", "mluw", "ttr", "total_words",
        "unintelligible_count", "unintelligible_ratio", "zero_vocalization_count",
        "nonverbal_vocalization_count", "question_ratio", "echolalia_count",
        "echolalia_ratio", "pronoun_reversal_count"
    ]
    
    # Task B: Multiclass
    multi_df = df[df["group"].isin(["ASD", "DD", "TD"])]
    X = multi_df[features].values
    y = multi_df["group"].astype(str).to_numpy()
    
    pipe = Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("sc", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42))
    ])
    pipe.fit(X, y)
    
    clf = pipe.named_steps["clf"]
    print("Classes:", clf.classes_)
    print("Intercepts:", clf.intercept_)
    print("Coefficients:")
    for idx, c in enumerate(clf.classes_):
        print(f"Class {c} ({idx}):")
        for f_name, coef in zip(features, clf.coef_[idx]):
            print(f"  {f_name}: {coef:.8f}")
else:
    print("combined_features.csv not found")
