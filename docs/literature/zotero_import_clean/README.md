# Zotero Clean Import Pack

Use this folder when you want to avoid duplicate Zotero items across collections.

Important:

- Import only the `.ris` files in this folder, one subcollection at a time.
- Do not also import `00_All_ASD_AI_Literature.ris` from the older `zotero_import/` folder.
- Each paper appears in exactly one primary collection here.
- Cross-cutting concepts such as `multimodal`, `ethics`, `privacy`, and `Thai-local-context` remain as Zotero tags (`KW` fields).

Recommended Zotero collection tree:

```text
AI_ASD_Literature_Review
- 01_Speech_Audio
- 02_Language_Text
- 03_Video_Behavior
- 04_Questionnaire_Screening
- 05_Multimodal_AI
- 06_Clinical_Ethics_Privacy
- 07_Review_Papers
- 08_Maybe_Exclude_Check
- 09_Thai_Local_Context
```

If you already imported duplicates into Zotero, use Zotero's `Duplicate Items` view and merge by DOI/title, or delete the imported collection and re-import from this clean pack.
