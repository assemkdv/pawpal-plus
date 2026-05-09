# Project Reflection

This is a personal reflection on building PawPal+, not technical documentation — see the root
`README.md` for how the current system actually works.

## Design

The scheduling engine (`Owner`, `Pet`, `Task`, `Scheduler`) started as a simple UML design:
pets belong to an owner, tasks belong to a pet, and a scheduler sorts, filters, and checks tasks
for conflicts. That structure held up well and is still the core of the app. One deliberate
simplification I kept: conflict detection only flags tasks at the *exact* same timestamp, not
overlapping time ranges. A range-overlap check would be more correct but adds real complexity for
a project of this size, and exact-match conflicts already catch the common case (double-booking
the same slot).

## Exploring an LLM backend, then simplifying

Partway through the project I replaced the rule-based assistant with an LLM-backed one — first
using the Anthropic API, then Google Gemini's free tier — with an agentic tool-use loop letting
the model call functions like `add_task` and `detect_conflicts` on its own. It worked, and it was
genuinely interesting to see the model decide on its own to check for conflicts when asked "what
does today look like?" without being told to.

I ultimately reverted that and shipped the simpler local version instead: rule-based command
parsing plus TF-IDF retrieval over a small knowledge base, with no external API calls at all. A
few reasons:

- **No dependency on an API key or a paid/rate-limited service.** Anyone cloning the repo can run
  it immediately.
- **Determinism.** The rule-based commands and TF-IDF retrieval behave the same way every time,
  which made the scheduling logic much easier to test and reason about.
- **Honesty about scope.** The knowledge base is a dozen hand-written sentences about dog and cat
  care. An LLM sitting on top of that doesn't add real capability, mostly just a more
  conversational wrapper — and it invites over-trusting the answers on something (pet health) where
  that matters.

The tradeoff is real: the current parser only understands a handful of exact command phrases, and
retrieval is pure keyword matching with no semantic understanding — so it's less flexible than the
LLM version was. For this project's size and purpose, I'd make the same call again.

## What I'd improve next

- Persistent storage — right now everything resets on refresh.
- A larger, better-organized knowledge base if the retrieval approach is kept.
- More graceful handling of phrasing the current keyword matching misses (synonyms, typos)
  without reintroducing a dependency on an external model.

## Key takeaway

Working with AI tools (VS Code Copilot and Claude Code) throughout this project reinforced that
the interesting design decisions are about scope and tradeoffs, not about which tool generates the
code. The most valuable moments were pushing back on suggestions that were correct in principle but
wrong for this project's constraints — like reverting the LLM-backed assistant once I decided a
fully local, deterministic system fit the project better.
