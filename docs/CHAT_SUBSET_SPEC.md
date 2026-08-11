# LinguaLens CHAT Subset Contract v1.7.0

Status: frozen engineering contract for the `v1.7.0-testbed` milestone. The
canonical parser/serializer and semantic round-trip verifier are implemented
in `apps/api/app/services/chat_subset.py` and
`apps/api/app/services/chat_roundtrip_service.py`. This remains an engineering
testbed contract; it is not a claim of clinical validation or full CHAT
compatibility.

## Version and encoding contract

- Subset: `lingualens-chat-v1.7.0`
- Parser: `lingualens-chat-parser-v1.7.0`
- Serializer: `lingualens-chat-serializer-v1.7.0`
- Files are UTF-8 without a byte-order mark, normalized to Unicode NFC.
- Serialized line endings are exactly `\n`; every artifact ends with one
  trailing `\n`.
- Thai code points, combining marks after NFC normalization, and Thai-English
  code switching must survive parse, semantic comparison, and re-export
  without transliteration or character substitution.
- Generated times are integer milliseconds. They are never rounded to a
  tolerance during a LinguaLens-generated round trip.

Every export records the subset, parser, and serializer versions. A version
change invalidates prior verification rather than silently reinterpreting it.

## Supported document structure

The canonical order is:

1. `@UTF8`
2. `@Begin`
3. `@Languages`
4. `@Participants`
5. one `@ID` row per participant
6. `@Media`, when the transcript is linked to audio
7. supported optional headers
8. speaker and dependent tiers in reviewed utterance order
9. `@End`

`@UTF8`, `@Begin`, `@Languages`, `@Participants`, and `@End` are supported
structural headers. `@Media` is required for an audio-derived artifact.
Supported optional metadata headers are `@Date`, `@Location`, `@Situation`,
`@Activities`, `@Comment`, `@Transcriber`, and `@Options`. Repeated optional
headers preserve occurrence order. Canonical output groups them in the order
listed above.

`@Participants` is a comma-separated list of `CODE Display_Name Role`
entries. Each code is uppercase ASCII, begins with a letter, and is unique.
`@ID` uses the CHAT pipe-delimited shape and must resolve to exactly one
declared participant. The canonical participant order is confirmed target
child, confirmed therapist, then other confirmed roles ordered by participant
code. `@Participants` and the corresponding `@ID` rows use that same order.
Names in synthetic fixtures are role labels, not real people.

LinguaLens-generated artifacts include the internal header
`@x-lingualens-utterance-id` immediately before each main tier so reviewed
utterance identity survives parse/re-export. It is part of the deterministic
serializer contract and is not clinical content.

`@Media` contains the artifact-safe media reference and media type. It must not
contain a storage key, signed URL, child identifier, local absolute path, or raw
uploaded filename. Artifact provenance carries the private media identifier
outside the downloadable CHAT content.

## Tiers, continuation, bullets, and annotations

A supported main tier is `*CODE:\tTEXT`, where `CODE` is declared in
`@Participants`. Main tiers retain canonical utterance order. A continuation
line starts with one tab and belongs to the immediately preceding main or
dependent tier. The semantic model preserves each continuation part; the
serializer wraps only at stored continuation boundaries, so repeated export is
byte-identical.

An audio-linked main tier may end with one media bullet:
`U+0015 START_END U+0015`, where `START` and `END` are base-10 integer
milliseconds, `0 <= START < END`, and both are within verified audio duration.
The canonical serializer emits no spaces inside the bullet. Generated bullets
must compare with exact millisecond equality.

The supported dependent tiers are:

- `%mor` — morphological analysis, preserved as reviewed structured text;
- `%gra` — grammatical relations, preserved as reviewed structured text;
- `%pho` — phonological transcription, preserved with Unicode fidelity;
- `%com` — utterance-local reviewer comment;
- `%act` — described non-speech action;
- `%sit` — utterance-local situation.

They must immediately follow their owner main tier and retain tier and
continuation order. No dependent tier is fabricated from ASR output.

Supported inline annotations are CHAT scoped groups `<...>`, repetition `[/]`,
retracing `[//]`, uncertainty `[?]`, coded error `[* CODE]`, explanation
`[= TEXT]`, event/paralinguistic description `[=! TEXT]`, filled pause `&-TEXT`,
partial word `&+TEXT`, nonword `&~TEXT`, and reviewed unintelligibility markers
`xxx`, `yyy`, and `www`. Pauses `(.)`, `(..)`, and `(...)` are preserved as
annotations rather than tokens. Annotation payloads are NFC text and must not
contain an unescaped control character.

Tabs delimit fields. Within text payloads, canonical escaping is `\\` for a
literal backslash, `\t` for a literal tab, and `\n` for an embedded logical
line break that is not a continuation boundary. Literal carriage returns,
NUL, unmatched `U+0015`, and other C0 controls are blocking errors.

## Unknown and unsupported content

Nothing may be silently discarded. Each unknown header, tier, or annotation
gets an action record with one of:

- `preserved_opaque`: extension content can be reproduced byte-for-byte after
  line-ending normalization and cannot change supported transcript meaning;
- `unsupported_non_blocking`: omission is proven not to affect supported
  meaning, but the omission and source location remain in provenance;
- `unsupported_blocking`: meaning or ownership is ambiguous, so candidate
  verification, attestation, and export stop.

Unknown `@x-*` headers and `%x*` dependent tiers may be
`preserved_opaque` when their owner and boundaries are unambiguous. An unknown
main tier, a dependent tier without an owner, duplicate participant code,
conflicting structural header, malformed bullet, unresolved `@ID`, annotation
that changes word scope, or unknown content that cannot be re-emitted is
`unsupported_blocking`. `unsupported_non_blocking` is allowed only by a
versioned rule that states why omission is semantically harmless; it is never a
default parser branch.

## Canonical semantic comparison

Round-trip comparison covers:

- language codes and their order;
- media reference and media type;
- participant code, role, display label, and parsed `@ID` fields;
- utterance ID and order, confirmed speaker code, reviewed NFC text,
  continuation parts, exact start/end milliseconds, terminator, dependent tier
  names/content/order, and annotations/content/scope/order;
- every opaque extension, its owner, source position, action, and content.

LinguaLens candidates use:

```text
canonical source -> export A -> parse A -> canonical B -> export B
```

The gate requires semantic equality and `sha256(export A) == sha256(export B)`.
Repeated export of the same canonical source and versions must be
byte-identical.

Each mismatch is structured with `code`, `field_or_tier`,
`utterance_or_segment_id`, `expected`, `actual`, `severity`,
`subset_version`, `parser_version`, and `serializer_version`. Errors are
returned as data; a generic success or lossy warning is not sufficient.

The only tolerant mode is the explicitly selected
`external-chat-import-v1.7.0` profile. It may normalize UTF-8 BOM, CRLF/CR line
endings, header order into canonical order, indentation, harmless wrapping, and
equivalent supported escaping. It may not tolerate changed Unicode text,
speaker identity, participant fields, tier ownership/content, annotation
scope, utterance order, or timestamps. Tolerance is never applied to generated
candidate/export verification.

## Artifact provenance and safety

Every candidate and final artifact records transcript version, speaker-mapping
version, verified audio and normalization versions, candidate verification ID,
attestation ID when applicable, subset/parser/serializer versions, canonical
checksum, export checksum, generation timestamp, and generating user/service.
The internal pre-attestation candidate is not downloadable. Final export is
allowed only from current attested inputs after the same round-trip gate.

The subset is a deterministic interchange contract for a research/education
prototype. It does not assert CHAT-wide compatibility, diagnose ASD, establish
norms, or establish Thai clinical validation.
