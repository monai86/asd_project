# Model Card v2

## Intended Use

This baseline is for review support only. It may support review priority,
contributing feature explanation, cohort similarity, and research dashboard
summaries. It is not a diagnostic tool and is not validated for Thai clinical
diagnosis.

## Dataset Source

Local public CHAT/CHA research transcripts and demo feature tables when present.
No private clinical data should be included by default.

## Dataset Size

2

## Class Distribution

- ASD: 1
- TD: 1

## Feature List

- child_utterance_count
- total_word_count
- number_of_different_words
- type_token_ratio
- mean_length_of_utterance_words
- unintelligible_ratio
- unknown_speaker_ratio
- question_ratio
- repetition_marker_count

## Baseline Models

- Logistic Regression
- Random Forest

## Metrics

- Logistic Regression: insufficient_data
- Random Forest: insufficient_data

## Dataset Warnings

- Insufficient labeled rows for train/test baseline evaluation.

## Limitations

- Public research corpora do not establish clinical validity for local practice.
- Small or imbalanced cohorts require caution and confidence intervals.
- Subgroup reports should warn when age, sex, or language cells are too small.
- Review cues are not diagnostic markers.

## Out-of-Scope Use

Automated diagnosis, unsupervised clinical triage, or labeling a child as normal
or abnormal.
