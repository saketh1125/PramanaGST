# Branch & Merge Rules

To maintain velocity while protecting the `main` branch, the following rules apply to all pull requests.

## 1. Contract Integrity
A Pull Request CANNOT be merged if it alters a Contract schema without a corresponding PR from the dependent team acknowledging the change. Breaking changes to `contracts/` require lead architect approval.

## 2. Automated Reviews
- All PRs must pass `pytest` suites.
- Code must be formatted with `ruff` and strictly typed with `mypy`.
- For the Graph team, Neo4j schema definitions must pass linting.

## 3. Human Reviews
For hackathon velocity, PRs require **1 approving review** from a peer. Cross-team reviews are highly encouraged but not strictly required unless editing a shared interface.

## 4. No Long-Lived Branches
Branches should live for a maximum of 48 hours. If a feature takes longer, it should be broken down into smaller, mergeable chunks hidden behind feature flags.
