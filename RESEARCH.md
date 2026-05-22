# Research Notes

## Design Summary
This project uses an inverted index with stemming, stop-word removal for term matching, and stored token positions for phrase and proximity queries.

The ranked search mode is intentionally lightweight and custom:
- TF-IDF is implemented directly from the stored postings so the repository does not depend on a heavier IR library.
- Phrase boosts favor exact phrase hits before looser proximity hits.
- Boolean operators are parsed in a small custom query layer so the behavior stays easy to inspect in tests.

## References
- [Introduction to Information Retrieval](https://nlp.stanford.edu/IR-book/) by Manning, Raghavan, and Schutze
- [TF-IDF overview](https://en.wikipedia.org/wiki/Tf%E2%80%93idf)
- [BM25 explanation](https://en.wikipedia.org/wiki/Okapi_BM25)
- [Inverted index basics](https://en.wikipedia.org/wiki/Inverted_index)
- [Pytest documentation](https://docs.pytest.org/)

## Alternatives Considered
- `scikit-learn` TF-IDF: rejected because the custom implementation already has access to the raw postings and keeps the dependency surface smaller.
- Full query parser with parentheses and precedence: deferred to keep the implementation compact and easy to reason about in this repository.
- External search engine services: out of scope for a self-contained educational crawler.

## Git And Release Workflow
- Use feature branches named `feature/<short-topic>` or `fix/<short-topic>`.
- Keep commits semantic and small, for example `feat(search): add tf-idf ranking`.
- Update `README.md` or `RESEARCH.md` when query behavior or benchmark expectations change.
- Before release, run tests, run benchmarks on the sample dataset, verify the CLI, and update a changelog entry.
- Tag releases with a versioned tag such as `v0.1.0`.

## Demo Outline
A 10-15 minute demo should cover:
- the crawl -> index -> query flow
- the inverted index and token normalization strategy
- the ranked search mode and query syntax
- benchmark results and what they mean
- trade-offs and limitations

## GenAI And Ethics
GenAI can help prototype, document, and generate test scaffolding, but the resulting behavior should be verified manually.

Verification expectations:
- confirm crawl output against the live site or a saved snapshot
- run the full test suite after behavioral changes
- inspect ranking changes on deterministic fixtures
- keep data provenance and benchmark settings reproducible

Critical commentary matters more than accepting model output at face value.
