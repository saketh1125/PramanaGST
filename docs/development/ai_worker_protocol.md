# AI Worker Protocol

PramanaGST utilizes Autonomous AI Agents (like Vertex AI / Gemini) as pair programmers and sub-agents. Human engineers must adhere to the following protocols when delegating tasks.

## 1. Context Boundary
When assigning a task to an AI worker, explicitly define the architectural layer. 
*Example:* "You are acting as a backend engineer on the Reconciliation Layer. Your task is constrained to `backend/reconciliation/`."

## 2. Contract Enforcement
Always provide the AI worker with the relevant Contract schemas. 
*Example:* "Here is `contract_1.json`. Write a Neo4j ingestion script that consumes this exact schema. Do not invent new fields."

## 3. Tool Constraints
AI workers are equipped with bash, python, and file-editing tools. Do not allow them to auto-run destructive commands (`rm -rf`) outside of `tmp/` or their designated module directories.

## 4. Artifact Generation
AI workers should generate Markdown artifacts (`task.md`, `implementation_plan.md`, `walkthrough.md`) for high-complexity tasks to allow human review before code execution.
