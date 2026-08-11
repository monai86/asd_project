# v1.7.0 CHAT golden expectations

The `.cha` files in this directory are synthetic, identifier-free fixtures.
Tests parse them with `parse_chat`, compare the canonical semantic model, and
verify deterministic re-export checksums.  Expected JSON records are generated
from the canonical model in the test runner so fixture line endings and
whitespace cannot silently become acceptance criteria.
