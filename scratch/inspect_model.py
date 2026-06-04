import joblib
from pathlib import Path

model_path = Path("artifacts/screening_model.joblib")
if model_path.exists():
    bundle = joblib.load(model_path)
    model = bundle["model"]
    
    # SimpleImputer -> StandardScaler -> LogisticRegression
    imputer = model.named_steps["imp"]
    scaler = model.named_steps["sc"]
    clf = model.named_steps["clf"]
    
    print("Imputer Medians:", imputer.statistics_)
    print("Scaler Means:", scaler.mean_)
    print("Scaler Scales:", scaler.scale_)
    print("LR Intercept:", clf.intercept_)
    print("LR Coefficients:", clf.coef_[0])
    
    features = bundle["features"]
    print("\nFeature Coefficients mapping:")
    for f, coef in zip(features, clf.coef_[0]):
        print(f"  {f}: {coef:.6f}")
else:
    print("Model not found")
