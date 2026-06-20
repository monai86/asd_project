import os
import sys
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, brier_score_loss, roc_auc_score, average_precision_score
from sklearn.model_selection import StratifiedGroupKFold, GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = "/Users/porschecaa/Desktop/asd-project"
sys.path.insert(0, PROJECT_ROOT)

from packages.ml.reference_dataset import build_canonical_reference_rows
from src.feature_schema import FEATURES

def _logit(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(probabilities, 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped))

def _lr_l1_pipeline(random_state: int, C: float) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(penalty="l1", solver="liblinear", class_weight="balanced", C=C, max_iter=2000, random_state=random_state)),
    ])

def _sensitivity(labels: np.ndarray, predictions: np.ndarray) -> float:
    _, _, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    return float(tp / (tp + fn)) if tp + fn else 0.0

def _specificity(labels: np.ndarray, predictions: np.ndarray) -> float:
    tn, fp, _, _ = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    return float(tn / (tn + fp)) if tn + fp else 0.0

def expected_calibration_error(labels: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> float:
    boundaries = np.linspace(0, 1, bins + 1)
    error = 0.0
    for index in range(bins):
        lower, upper = boundaries[index], boundaries[index + 1]
        mask = (probabilities >= lower) & (probabilities <= upper if index == bins - 1 else probabilities < upper)
        if not mask.any():
            continue
        error += float(mask.mean()) * abs(float(probabilities[mask].mean()) - float(labels[mask].mean()))
    return float(error)

def _participant_bootstrap_sensitivity(predictions: pd.DataFrame, n_bootstrap: int, random_state: int) -> dict[str, float]:
    participants = predictions["participant_key"].drop_duplicates().to_numpy()
    rng = np.random.default_rng(random_state)
    values: list[float] = []
    for _ in range(n_bootstrap):
        sampled = rng.choice(participants, size=len(participants), replace=True)
        sample = pd.concat([predictions[predictions["participant_key"] == p] for p in sampled], ignore_index=True)
        sample_active = sample[~sample["abstained"]]
        labels = sample_active["label"].to_numpy(dtype=int)
        if len(labels) == 0 or labels.sum() == 0:
            continue
        values.append(_sensitivity(labels, sample_active["prediction"].to_numpy(dtype=int)))
    if not values:
        return {"lower": 0.0, "upper": 0.0, "mean": 0.0}
    return {
        "lower": float(np.percentile(values, 2.5)),
        "upper": float(np.percentile(values, 97.5)),
        "mean": float(np.mean(values)),
    }

def optimize_threshold_and_margin(cal_probs, cal_labels, target_sens, default_margin=0.1):
    best_t = 0.5
    best_m = default_margin
    best_spec = -1.0
    
    for t in np.arange(0.2, 0.8, 0.01):
        for m in [0.05, 0.1, 0.15]:
            abstained = (cal_probs >= t - m) & (cal_probs < t + m)
            abst_rate = abstained.mean()
            if abst_rate > 0.38: # Allow up to 38% abstention on calibration fold
                continue
                
            non_abstained = ~abstained
            if not non_abstained.any():
                continue
                
            active_labels = cal_labels[non_abstained]
            active_preds = (cal_probs[non_abstained] >= t).astype(int)
            
            sens = _sensitivity(active_labels, active_preds)
            spec = _specificity(active_labels, active_preds)
            
            if sens >= target_sens:
                if spec > best_spec:
                    best_spec = spec
                    best_t = t
                    best_m = m
                    
    if best_spec == -1.0:
        best_sens = -1.0
        for t in np.arange(0.2, 0.8, 0.01):
            for m in [0.05, 0.1, 0.15]:
                abstained = (cal_probs >= t - m) & (cal_probs < t + m)
                if abstained.mean() > 0.38:
                    continue
                non_abstained = ~abstained
                if not non_abstained.any():
                    continue
                active_labels = cal_labels[non_abstained]
                active_preds = (cal_probs[non_abstained] >= t).astype(int)
                sens = _sensitivity(active_labels, active_preds)
                if sens > best_sens:
                    best_sens = sens
                    best_t = t
                    best_m = m
                    best_spec = _specificity(active_labels, active_preds)
                    
    return best_t, best_m

def run_eval(features, labels, groups, pipeline_func, target_sens):
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    probabilities = np.zeros(len(features))
    predictions = np.zeros(len(features), dtype=int)
    uncertain = np.zeros(len(features), dtype=bool)
    
    for fold, (train_index, test_index) in enumerate(splitter.split(features, labels, groups), start=1):
        train_features = features.iloc[train_index]
        train_labels = labels[train_index]
        train_groups = groups[train_index]
        
        cal_model = None
        for offset in range(20):
            gs = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42 + fold + offset)
            fit_idx, cal_idx = next(gs.split(train_features, train_labels, train_groups))
            if len(np.unique(train_labels[fit_idx])) < 2 or len(np.unique(train_labels[cal_idx])) < 2:
                continue
                
            estimator = pipeline_func(42 + fold + offset)
            estimator.fit(train_features.iloc[fit_idx], train_labels[fit_idx])
            
            raw_probs = estimator.predict_proba(train_features.iloc[cal_idx])[:, 1]
            calibrator = LogisticRegression(max_iter=1000, random_state=42 + fold + offset)
            calibrator.fit(_logit(raw_probs).reshape(-1, 1), train_labels[cal_idx])
            
            cal_probs = calibrator.predict_proba(_logit(raw_probs).reshape(-1, 1))[:, 1]
            cal_lbls = train_labels[cal_idx]
            
            t_opt, m_opt = optimize_threshold_and_margin(cal_probs, cal_lbls, target_sens)
            cal_model = (estimator, calibrator, t_opt, m_opt)
            break
            
        if cal_model is None:
            estimator = pipeline_func(42 + fold)
            estimator.fit(train_features, train_labels)
            cal_model = (estimator, None, 0.5, 0.1)
            
        estimator, calibrator, t_opt, m_opt = cal_model
        
        test_raw = estimator.predict_proba(features.iloc[test_index])[:, 1]
        if calibrator is not None:
            test_probs = calibrator.predict_proba(_logit(test_raw).reshape(-1, 1))[:, 1]
        else:
            test_probs = test_raw
            
        probabilities[test_index] = test_probs
        predictions[test_index] = (test_probs >= t_opt).astype(int)
        uncertain[test_index] = (test_probs >= t_opt - m_opt) & (test_probs < t_opt + m_opt)

    non_abstained = ~uncertain
    active_labels = labels[non_abstained]
    active_preds = predictions[non_abstained]
    
    sens = _sensitivity(active_labels, active_preds)
    spec = _specificity(active_labels, active_preds)
    abst_rate = float(uncertain.mean())
    
    prediction_rows = pd.DataFrame({
        "participant_key": groups,
        "label": labels,
        "prediction": predictions,
        "abstained": uncertain
    })
    ci = _participant_bootstrap_sensitivity(prediction_rows, n_bootstrap=100, random_state=42)
    return sens, ci["lower"], ci["upper"], spec, abst_rate

def main():
    print("Loading data...")
    combined = pd.read_csv(os.path.join(PROJECT_ROOT, "data/combined_features.csv"))
    curated = pd.read_csv(os.path.join(PROJECT_ROOT, "data/curated_group_features.csv"))
    key = b"12345678901234567890123456789012"
    canonical = build_canonical_reference_rows(combined, curated, pseudonymization_key=key)
    rows = canonical.rows
    
    valid = rows[rows["original_group"].isin(["TD", "DD", "ASD", "LT", "STI", "HL"])].copy()
    valid["label"] = (valid["original_group"] != "TD").astype(int)
    valid = valid.reset_index(drop=True)
    
    features = valid[FEATURES]
    labels = valid["label"].to_numpy(dtype=int)
    groups = valid["participant_key"].to_numpy()
    
    print("\n=== L1 Regularized Logistic Regression Sweep ===")
    for C in [0.06, 0.08, 0.10, 0.12, 0.15]:
        for target in [0.85, 0.86, 0.87, 0.88]:
            p_func = lambda rs: _lr_l1_pipeline(rs, C)
            sens, ci_l, ci_u, spec, abst = run_eval(features, labels, groups, p_func, target)
            print(f"L1 C={C:.2f}, Target Sens {target:.2f} -> Active Sens: {sens:.4f} (95% CI: [{ci_l:.4f}, {ci_u:.4f}]), Spec: {spec:.4f}, Abstention: {abst:.4f}")

if __name__ == "__main__":
    main()
