# Edge Case Checklist — Adapted from AionUi Testing Skill

A compact checklist for test coverage completeness. Use during test writing and review.

## The Checklist

Before submitting a test or claiming coverage complete, verify:

- [ ] `null` / `undefined` inputs handled
- [ ] Empty arrays/objects handled  
- [ ] Errors thrown by dependencies handled (network failure, DB timeout, malformed response)
- [ ] Boundary values tested (0, -1, max, empty string, past dates)
- [ ] Async operations verified (timeout, rejection, cancellation, out-of-order resolution)

## Who Each Check Catches

| Check | Bug type it prevents |
|---|---|
| null/undefined | `Cannot read properties of null` crash at runtime |
| Empty arrays/objects | `.map()` on empty returns nothing silently; `.filter(Boolean)` on empty misleads |
| Dependency error | 500 response renders blank page instead of error state |
| Boundary values | Pagination off-by-one, counting logic, date range edge |
| Async | Race conditions, stale closure, unhandled promise rejection |

## Where to Apply

- **Unit tests** — check pure logic functions and hooks against all 5 categories
- **Integration tests** — focus on dependency-error and async checks  
- **Component tests** — focus on null/undefined and boundary-value checks for props and state

## Source

Adapted from the [AionUi testing skill](https://github.com/iOfficeAI/AionUi) by iOfficeAI (Apache-2.0).
