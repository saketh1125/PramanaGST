# Git Strategy

We use a simplified Trunk-Based Development model optimized for rapid iteration and hackathon pacing.

## Branching Model
- `main`: The single source of truth. Must always be deployable.
- Feature branches: Created off `main` and merged back via Pull Request.

## Branch Naming Convention
Branches should clearly indicate the layer they belong to:
- `ingestion/feature-name`
- `graph/feature-name`
- `recon/feature-name`
- `risk/feature-name`
- `api/feature-name`
- `ui/feature-name`

## Commit Messages
Use conventional commits to auto-generate changelogs:
- `feat(graph): Add Cypher index for IRN lookup`
- `fix(api): Resolve CORS issue on GraphQL endpoint`
- `docs(ingestion): Update normalization rules`
- `chore: Update Pydantic to v2.6`
