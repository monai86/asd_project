# Zotero Import Pack

Import these RIS files into Zotero one collection at a time.

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

This pack writes RIS files for non-empty primary collections. Use Zotero tags to find cross-cutting groups such as `multimodal`, `ethics`, or `privacy` when those papers are primarily stored under speech/audio or video/behavior.

Fast path:

1. Create the parent collection `AI_ASD_Literature_Review` in Zotero.
2. Create subcollections matching the RIS filenames.
3. Select a subcollection, then use `File > Import...` and choose the matching `.ris` file.
4. Keep Zotero's imported tags. They are written as RIS `KW` fields.
5. For items with incomplete metadata, use Zotero's DOI/URL lookup or open the linked PubMed/IEEE/PMC page.

You can also import `00_All_ASD_AI_Literature.ris` into one collection first, but Zotero will not automatically split it into subcollections.
