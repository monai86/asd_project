"""
Deep-learning classifier (PyTorch) for screening ASD vs non-ASD.

Two complementary models are trained:

    1. TabularMLP   -- a plain multi-layer perceptron that consumes the
                       hand-engineered CHAT features already produced by
                       data_loader.py.  Directly comparable to the
                       sklearn baselines in classifier.py.

    2. UtteranceLSTM -- a small bidirectional LSTM that reads the
                        *sequence* of CHI utterances from each transcript
                        (one word-count vector per utterance).  Shows that
                        a sequence model can pick up temporal speech
                        patterns that aggregate features miss.

Both are evaluated with stratified 5-fold CV so the numbers are directly
comparable with `src/classifier.py`.

Outputs:
    reports/metrics/deep_learning_results.csv
    reports/figures/deep_learning_roc.png
    reports/figures/deep_learning_training_curves.png
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pylangacq as pla
import seaborn as sns
import torch
import torch.nn as nn
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Dataset

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FIG_DIR = PROJECT_ROOT / "reports" / "figures"
METRIC_DIR = PROJECT_ROOT / "reports" / "metrics"
FIG_DIR.mkdir(parents=True, exist_ok=True)
METRIC_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="talk")

FEATURES = [
    "age_months", "total_utterances", "mlu", "mluw", "ttr", "total_words",
    "unintelligible_count", "unintelligible_ratio",
    "zero_vocalization_count", "nonverbal_vocalization_count",
    "question_ratio",
]

RANDOM_STATE = 42
DEVICE = torch.device("cuda" if torch.cuda.is_available()
                     else "mps" if torch.backends.mps.is_available()
                     else "cpu")
print(f"[info] using device: {DEVICE}")

torch.manual_seed(RANDOM_STATE)
np.random.seed(RANDOM_STATE)


# =========================================================================
# Model 1: Tabular MLP on hand-engineered features
# =========================================================================
class TabularMLP(nn.Module):
    def __init__(self, in_dim: int, hidden: int = 64, dropout: float = 0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, hidden // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden // 2, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


def _train_mlp(X_tr, y_tr, X_va, y_va, in_dim: int,
               epochs: int = 200, lr: float = 1e-3,
               weight_decay: float = 1e-4) -> Tuple[TabularMLP, List[float], List[float]]:
    model = TabularMLP(in_dim).to(DEVICE)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    # class imbalance weighting
    pos = float((y_tr == 1).sum())
    neg = float((y_tr == 0).sum())
    pos_weight = torch.tensor([neg / max(pos, 1.0)], device=DEVICE)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    X_tr_t = torch.tensor(X_tr, dtype=torch.float32, device=DEVICE)
    y_tr_t = torch.tensor(y_tr, dtype=torch.float32, device=DEVICE)
    X_va_t = torch.tensor(X_va, dtype=torch.float32, device=DEVICE)
    y_va_t = torch.tensor(y_va, dtype=torch.float32, device=DEVICE)

    tr_losses, va_losses = [], []
    best_state, best_va = None, float("inf")
    patience, bad = 30, 0

    for _ in range(epochs):
        model.train()
        opt.zero_grad()
        out = model(X_tr_t)
        loss = loss_fn(out, y_tr_t)
        loss.backward()
        opt.step()
        tr_losses.append(loss.item())

        model.eval()
        with torch.no_grad():
            va_loss = loss_fn(model(X_va_t), y_va_t).item()
        va_losses.append(va_loss)

        if va_loss < best_va - 1e-4:
            best_va = va_loss
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            bad = 0
        else:
            bad += 1
            if bad >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model, tr_losses, va_losses


def run_tabular_mlp(df: pd.DataFrame):
    X = df[FEATURES].values.astype(np.float32)
    y = (df["group"] == "ASD").astype(int).values

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    all_pred = np.zeros(len(y))
    all_prob = np.zeros(len(y))
    fold_curves = []

    for fold, (tr_idx, va_idx) in enumerate(skf.split(X, y), 1):
        imp = SimpleImputer(strategy="median")
        sc = StandardScaler()
        X_tr = sc.fit_transform(imp.fit_transform(X[tr_idx]))
        X_va = sc.transform(imp.transform(X[va_idx]))
        y_tr, y_va = y[tr_idx], y[va_idx]

        model, tr_l, va_l = _train_mlp(X_tr, y_tr, X_va, y_va, in_dim=X.shape[1])
        fold_curves.append((tr_l, va_l))

        model.eval()
        with torch.no_grad():
            logits = model(torch.tensor(X_va, dtype=torch.float32, device=DEVICE))
            prob = torch.sigmoid(logits).cpu().numpy()
        all_prob[va_idx] = prob
        all_pred[va_idx] = (prob >= 0.5).astype(int)
        print(f"  fold {fold}  epochs={len(tr_l):3d}  "
              f"val-loss={va_l[-1]:.3f}  val-auc={roc_auc_score(y_va, prob):.3f}")

    return y, all_pred, all_prob, fold_curves


# =========================================================================
# Model 2: Utterance-sequence Bi-LSTM
# =========================================================================
# Simple bag-of-features per utterance:
#   [ word_count, has_xxx, has_yyy, is_zero, is_question, has_nonverbal ]
# This stays compatible with any CHAT file and doesn't need a vocabulary.
UTT_FEATS = 6
MAX_UTT = 200  # truncate / pad to this many CHI utterances per file


def _utt_vector(utterance, raw_tier: str) -> np.ndarray:
    word_count = sum(
        1 for t in utterance.tokens
        if t.word and t.word not in {".", "?", "!", ",", ";", ":",
                                     "+...", "+..", "+/.", "+//.", "+/?"}
    )
    has_xxx = int("xxx" in raw_tier)
    has_yyy = int("yyy" in raw_tier)
    stripped = raw_tier.strip().rstrip(" .?!").strip()
    is_zero = int(stripped == "0")
    is_q = int(raw_tier.rstrip().endswith("?"))
    has_nonverb = int("&=" in raw_tier)
    return np.array([word_count, has_xxx, has_yyy, is_zero, is_q, has_nonverb],
                    dtype=np.float32)


def _file_to_sequence(cha_path: Path) -> np.ndarray:
    try:
        r = pla.read_chat(str(cha_path))
    except Exception:
        r = pla.read_chat(str(cha_path), strict=False)
    seq = []
    for u in r.utterances():
        if u.participant != "CHI":
            continue
        raw = u.tiers.get("CHI", "")
        seq.append(_utt_vector(u, raw))
        if len(seq) >= MAX_UTT:
            break
    if not seq:
        return np.zeros((1, UTT_FEATS), dtype=np.float32)
    return np.stack(seq)


def _resolve_cha_path(row: pd.Series) -> Path:
    """Reconstruct the original .cha path from the combined CSV row."""
    corpus = row["corpus"]
    pid = row["participant_id"]
    if corpus == "eigsti":
        return DATA_DIR / "Eigsti" / row["group"] / f"{pid}.cha"
    if corpus == "nadig":
        return DATA_DIR / "Nadig" / f"{pid}.cha"
    raise ValueError(f"unknown corpus: {corpus}")


class SeqDataset(Dataset):
    def __init__(self, seqs, labels):
        self.seqs = seqs
        self.labels = labels

    def __len__(self):
        return len(self.seqs)

    def __getitem__(self, i):
        return self.seqs[i], self.labels[i]


def _collate(batch):
    seqs, ys = zip(*batch)
    lens = [s.shape[0] for s in seqs]
    max_len = max(lens)
    padded = np.zeros((len(seqs), max_len, UTT_FEATS), dtype=np.float32)
    for i, s in enumerate(seqs):
        padded[i, :s.shape[0]] = s
    return (torch.tensor(padded),
            torch.tensor(lens),
            torch.tensor(np.asarray(ys), dtype=torch.float32))


class UtteranceLSTM(nn.Module):
    def __init__(self, in_dim=UTT_FEATS, hidden=32, dropout=0.3):
        super().__init__()
        self.lstm = nn.LSTM(in_dim, hidden, batch_first=True,
                            bidirectional=True)
        self.drop = nn.Dropout(dropout)
        self.head = nn.Linear(2 * hidden, 1)

    def forward(self, x, lens):
        packed = nn.utils.rnn.pack_padded_sequence(
            x, lens.cpu(), batch_first=True, enforce_sorted=False
        )
        _, (h, _) = self.lstm(packed)            # h: (2, B, H)
        h = torch.cat([h[0], h[1]], dim=-1)      # (B, 2H)
        return self.head(self.drop(h)).squeeze(-1)


def run_lstm(df: pd.DataFrame):
    print("\n[LSTM] building per-utterance sequences...")
    seqs, labels = [], []
    for _, row in df.iterrows():
        try:
            path = _resolve_cha_path(row)
            seqs.append(_file_to_sequence(path))
            labels.append(int(row["group"] == "ASD"))
        except Exception as e:  # noqa: BLE001
            print(f"  skip {row['participant_id']}: {e}")
    labels = np.array(labels)
    lens = [s.shape[0] for s in seqs]
    print(f"[LSTM] {len(seqs)} sequences, "
          f"len: min={min(lens)} max={max(lens)} median={int(np.median(lens))}")

    # Normalize sequence features using training-set stats per fold
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    all_pred = np.zeros(len(labels))
    all_prob = np.zeros(len(labels))

    for fold, (tr_idx, va_idx) in enumerate(skf.split(np.zeros(len(labels)), labels), 1):
        # fit scaler on training utterances
        train_concat = np.concatenate([seqs[i] for i in tr_idx], axis=0)
        mu = train_concat.mean(0, keepdims=True)
        sd = train_concat.std(0, keepdims=True) + 1e-6
        tr_seqs = [(seqs[i] - mu) / sd for i in tr_idx]
        va_seqs = [(seqs[i] - mu) / sd for i in va_idx]
        y_tr, y_va = labels[tr_idx], labels[va_idx]

        model = UtteranceLSTM().to(DEVICE)
        opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        pos = float((y_tr == 1).sum())
        neg = float((y_tr == 0).sum())
        pw = torch.tensor([neg / max(pos, 1.0)], device=DEVICE)
        loss_fn = nn.BCEWithLogitsLoss(pos_weight=pw)

        tr_loader = DataLoader(SeqDataset(tr_seqs, y_tr),
                               batch_size=8, shuffle=True, collate_fn=_collate)
        va_loader = DataLoader(SeqDataset(va_seqs, y_va),
                               batch_size=16, shuffle=False, collate_fn=_collate)

        best_state, best_va, bad = None, float("inf"), 0
        for epoch in range(60):
            model.train()
            for x, lens_b, y in tr_loader:
                x, lens_b, y = x.to(DEVICE), lens_b.to(DEVICE), y.to(DEVICE)
                opt.zero_grad()
                loss = loss_fn(model(x, lens_b), y)
                loss.backward()
                opt.step()

            model.eval()
            with torch.no_grad():
                va_losses = []
                for x, lens_b, y in va_loader:
                    x, lens_b, y = x.to(DEVICE), lens_b.to(DEVICE), y.to(DEVICE)
                    va_losses.append(loss_fn(model(x, lens_b), y).item())
                va_mean = float(np.mean(va_losses))
            if va_mean < best_va - 1e-4:
                best_va = va_mean
                best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
                bad = 0
            else:
                bad += 1
                if bad >= 10:
                    break

        if best_state is not None:
            model.load_state_dict(best_state)

        # predict on validation set (keep original order)
        model.eval()
        probs = np.zeros(len(va_idx))
        with torch.no_grad():
            idx = 0
            for x, lens_b, _ in DataLoader(SeqDataset(va_seqs, y_va),
                                            batch_size=16, shuffle=False,
                                            collate_fn=_collate):
                x, lens_b = x.to(DEVICE), lens_b.to(DEVICE)
                p = torch.sigmoid(model(x, lens_b)).cpu().numpy()
                probs[idx:idx + len(p)] = p
                idx += len(p)
        all_prob[va_idx] = probs
        all_pred[va_idx] = (probs >= 0.5).astype(int)
        print(f"  fold {fold}  val-auc={roc_auc_score(y_va, probs):.3f}")

    return labels, all_pred, all_prob


# =========================================================================
# Runner
# =========================================================================
def _plot_training_curves(fold_curves):
    fig, ax = plt.subplots(figsize=(9, 5))
    for i, (tr, va) in enumerate(fold_curves, 1):
        ax.plot(tr, alpha=0.4, label=f"fold{i} train" if i == 1 else None,
                color="tab:blue")
        ax.plot(va, alpha=0.7, label=f"fold{i} val" if i == 1 else None,
                color="tab:orange")
    ax.set_title("TabularMLP training curves (5 folds)")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("BCE loss")
    ax.legend()
    fig.tight_layout()
    out = FIG_DIR / "deep_learning_training_curves.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved  {out.relative_to(PROJECT_ROOT)}")


def _plot_roc(y, results: dict):
    fig, ax = plt.subplots(figsize=(7, 6))
    for name, prob in results.items():
        fpr, tpr, _ = roc_curve(y, prob)
        auc = roc_auc_score(y, prob)
        ax.plot(fpr, tpr, label=f"{name} (AUC={auc:.3f})", linewidth=2.2)
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("Deep learning: ASD vs non-ASD")
    ax.legend()
    fig.tight_layout()
    out = FIG_DIR / "deep_learning_roc.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved  {out.relative_to(PROJECT_ROOT)}")


def main() -> None:
    df = pd.read_csv(DATA_DIR / "combined_features.csv").dropna(subset=["group"])
    print(f"Loaded {len(df)} rows.")

    # -- TabularMLP --
    print("\n" + "=" * 70)
    print("Model 1: Tabular MLP (hand-engineered features)")
    print("=" * 70)
    y, mlp_pred, mlp_prob, curves = run_tabular_mlp(df)
    _plot_training_curves(curves)

    # -- UtteranceLSTM --
    print("\n" + "=" * 70)
    print("Model 2: Utterance-sequence Bi-LSTM")
    print("=" * 70)
    y2, lstm_pred, lstm_prob = run_lstm(df)
    assert np.array_equal(y, y2), "label order mismatch"

    rows = []
    for name, pred, prob in [
        ("TabularMLP", mlp_pred, mlp_prob),
        ("UtteranceLSTM", lstm_pred, lstm_prob),
    ]:
        acc = accuracy_score(y, pred)
        f1 = f1_score(y, pred, average="macro")
        auc = roc_auc_score(y, prob)
        rows.append({"model": name,
                     "accuracy": round(acc, 4),
                     "f1_macro": round(f1, 4),
                     "roc_auc": round(auc, 4)})
        print(f"\n[{name}]")
        print(classification_report(y, pred, target_names=["non-ASD", "ASD"],
                                    digits=3))

    _plot_roc(y, {"TabularMLP": mlp_prob, "UtteranceLSTM": lstm_prob})

    out = METRIC_DIR / "deep_learning_results.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\n[saved] {out.relative_to(PROJECT_ROOT)}")
    print("\n=== SUMMARY ===")
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
