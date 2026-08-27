# Portfolio README and Repository Positioning Design

## Goal

Reposition the repository as an Applied AI portfolio project: a multi-channel, multi-user AI chatbot platform with a QQ reference deployment and a validated Discord deployment. The project should demonstrate AI-system design, user-informed iteration, and backend reliability without overstating channel coverage or code ownership.

## Repository metadata

- Rename the GitHub repository to `multichannel-ai-chatbot-platform`.
- Set a concise description focused on layered LLM moderation, persona RAG, long-term memory, and reliable Docker deployment.
- Add recruiter-facing topics for AI chatbots, LLM systems, RAG, Docker Compose, Python, SQLite, and multi-channel messaging.
- Preserve the current Git remote by updating its URL after the GitHub rename.

## Documentation structure

- Replace `README.md` with an English default README.
- Add `README.zh-CN.md` as a complete Chinese counterpart.
- Put reciprocal language links at the top of both documents.
- Mark the project as a completed portfolio project, not an archived or actively maintained product.
- Keep the current deployment and safety instructions, but move them after the project value, evidence, architecture, contributions, and technology sections.

## Claims and evidence

The English README will distinguish the scope of each claim:

- QQ is the long-running reference deployment: a 5,000+ member community, 5,689 requests over 22 days, and 300+ active users during that period.
- Discord was end-to-end validated for connection, message reception, and model-backed replies, but has no long-running operational claim.
- The platform architecture can extend to channels supported by AstrBot; the repository will not claim that all supported channels have ready-to-use deployment configurations.
- SQLite WAL and targeted PRAGMA tuning eliminated observed `database is locked` failures during subsequent operation. The README will not claim a generic throughput increase.
- A user-feedback survey collected 25 responses from 44 views (56% response rate). README evidence will be limited to anonymized aggregate findings: 64% valued reliable reactive replies and 60% valued persistent group preferences and memories.

## Ownership and attribution

- Clearly label original work: web data collection and knowledge preparation, the multi-layer routing/moderation funnel, time- and event-aware persona behavior, the QQ sticker-capture replacement plugin, and the associated testing/operational configuration.
- Describe RAG and long-term memory as deeply integrated and extended framework/plugin capabilities, rather than claiming the underlying frameworks were authored from scratch.
- Describe `enhance-mode` and `life-scheduler` as substantial redesigns/extensions inspired by upstream AstrBot plugins, while identifying the user-designed funnel and event logic.
- Describe AstrBot accurately as the underlying multi-platform LLM and plugin framework. Do not claim that it uses LangChain.

## README content order

1. Project name, language links, portfolio status, and one-sentence value proposition.
2. Outcome metrics and channel-validation scope.
3. Problem statement: safe, context-aware AI interaction in multi-user chat environments.
4. Layered message-flow architecture diagram.
5. Applied AI capabilities: persona, web-sourced knowledge preparation, RAG, long-term memory, routing, and time/event-aware behavior.
6. Reliability, privacy, and safety controls.
7. User-informed iteration with anonymized aggregate survey results.
8. Technology stack grouped by responsibility.
9. Ownership/attribution notes, project layout, setup guide, safety guide, and references.

## Privacy requirements

- Remove the tracked raw survey CSV from the default branch.
- Add ignore rules for raw survey exports.
- Do not link survey exports, screenshots, raw data, IP addresses, user agents, geographic fields, or individual responses from the README.
- Keep only the aggregate report after correcting it from 24 to 25 responses and aligning the cited counts.

## Validation

- Check that both README files render as valid Markdown with working reciprocal links and no stale "archived" claim.
- Check that all metrics match the 25-row raw CSV and are consistently worded.
- Check that the raw survey CSV is removed from the current tracked tree and protected by `.gitignore`.
- Verify GitHub rename metadata and the local `origin` URL after the remote operation.
