# ASD Clinical ML Review Checklist

## Data Integrity

- Confirm no child/session duplicate crosses evaluation boundaries.
- Confirm labels come from source metadata and are not inferred from folder names inconsistently.
- Confirm corpus-specific artifacts are not the main classifier signal.
- Confirm feature columns match between training, dashboard prediction, and XAI display.

## Evaluation

- Report sample size, class counts, and split method.
- Prefer stratified or group-aware validation when possible.
- Include confusion matrix plus sensitivity/specificity for screening claims.
- Treat AUC as ranking performance, not clinical deployment proof.
- Flag any threshold tuned on test data.

## Explainability

- Verify feature ordering and preprocessing match the model.
- Explain contributions as "pushed the model output", not "caused ASD".
- Keep explanations understandable for non-technical clinical readers.

## Clinical Language

Use:

- "screening result"
- "risk estimate"
- "supports further assessment"
- "research prototype"
- "not a diagnostic tool"

Avoid:

- "diagnoses ASD"
- "detects autism definitively"
- "clinically validated" unless backed by external validation
- "FDA-like" unless carefully framed as inspired by published designs
