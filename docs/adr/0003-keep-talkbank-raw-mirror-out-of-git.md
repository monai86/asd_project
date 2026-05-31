# Keep TalkBank raw mirror out of git

TalkBank corpus files are useful for repeatable research processing, but raw
downloads carry license, access, and repository-size constraints. We will keep
the TalkBank Raw Mirror under ignored local paths and track only corpus
manifests, checksums, and QC summaries so future runs can audit what was used
without publishing protected raw transcript or media files.
