# Paper Screening Criteria

Project focus: AI-assisted speech/language assessment or screening support for autism spectrum disorder (ASD), framed as a decision-support workflow for speech-language professionals rather than a diagnostic replacement.

## Source Table

Use `paper_screening_table.csv` as the working screening table.

Important rule: AI priority is only a sorting aid. Final inclusion must be based on manual reading of the title, abstract, and full text.

## Screening Stages

### Stage 1: Title Screening

Read the title and metadata. Mark `include`, `maybe`, or `exclude`.

Include or maybe if the paper appears to involve:

- ASD, autism, autism traits, or neurodevelopmental conditions clearly connected to ASD.
- AI, machine learning, deep learning, NLP, algorithmic screening, computational analysis, or digital phenotyping.
- Speech, audio, voice, acoustic, prosody, language, transcript, communication, clinical screening, assessment, or diagnosis-support workflows.
- Thai/local clinical context relevant to ASD assessment or screening.
- Review papers that summarize AI-based ASD screening, speech/audio markers, clinical validity, ethics, or implementation gaps.

Exclude at title stage if clearly:

- Not about ASD or autism traits.
- Not about AI/ML/computational/digital screening or assessment.
- Only about treatment/intervention with no assessment, screening, measurement, or clinical decision-support relevance.
- A modality far from the current project, unless useful for future multimodal context.

### Stage 2: Abstract Screening

Read the abstract yourself. Fill the manual abstract columns.

Keep the paper if the abstract reports enough information about:

- Population or sample.
- Data modality, such as speech, audio, transcript, language, video, questionnaire, EHR, or multimodal data.
- AI/ML/NLP method or computational approach.
- Screening, assessment, severity estimation, diagnosis support, clinical workflow, or validation outcome.
- Relevance to speech-language assessment, clinical screening, Thai context, or research-gap framing.

Move to `maybe` if promising but incomplete. Exclude if the abstract shows the paper is only broadly about mental health AI or not tied to ASD assessment.

### Stage 3: Full-Text Screening

Read the full text before final inclusion. Fill the full-text manual columns.

Final inclusion requires enough evidence to extract:

- Sample size or participant description.
- Dataset/source of data.
- Study design.
- Model/method.
- Evaluation metrics, such as accuracy, sensitivity, specificity, F1, AUC, calibration, validation strategy, or qualitative validation.
- Key limitations reported by authors.
- Clear relevance to this project.

If the paper lacks method, dataset, or metrics, it can still be used as background, but not as strong evidence for model performance or clinical usefulness.

## Inclusion Criteria

- Published or available from 2019-2026, unless it is a key Thai/local validation paper or foundational background source.
- Focuses on ASD/autism assessment, screening, detection, severity, traits, diagnosis support, or clinical decision support.
- Uses or reviews AI/ML/deep learning/NLP/computational methods, or provides a clinically relevant local ASD assessment context.
- Has enough information to support a literature matrix entry.
- Prefer papers with available PDF/full text.

## Exclusion Criteria

- Not ASD-related.
- No AI/ML/computational method and no local clinical-context value.
- Opinion/editorial only, unless used strictly as background or ethics context.
- No usable abstract or full text for evidence extraction.
- Reports performance claims without enough information about dataset, validation, or metrics.
- Duplicate or superseded record.
- Animal-only or non-human study, unless explicitly used as distant background and marked as such.

## Priority Guide

High priority:

- Speech/audio/language/transcript papers.
- Thai/local ASD screening or assessment papers.
- Review/meta-analysis/scoping review papers that cover speech, voice, text, AI screening, clinical validity, or implementation gaps.

Medium priority:

- Clinical screening, questionnaire, video/behavior, eye tracking, multimodal, or mobile-app papers.
- Broad AI-ASD review papers useful for background.

Low priority:

- Neuroimaging-only, EEG-only, general mental-health AI, intervention-only, education-only, or distant modality papers.
- Missing-PDF papers that are not central to the review question.

## Suggested Target Counts

- Start: 88 papers in the Zotero master list.
- After title screening: about 35-45 papers.
- After abstract screening: about 20-30 papers.
- After full-text screening: about 10-15 core papers plus 5-8 background/context papers.

## Manual Notes Standard

Use `not reported` when the paper does not state a detail.

Do not infer sample size, dataset, model, metrics, or clinical validity from the title alone.

Use cautious wording for final review claims. Present AI as screening support, decision support, workflow assistance, or progress tracking support, not as a replacement for clinicians.
