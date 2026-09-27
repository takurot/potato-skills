---
name: docs-canvas
description: "[Experimental] Render a documentation-style Cursor Canvas that organizes architecture notes, API references, walkthroughs, and how-tos into a navigable layout with sections, tables of contents, and cross-references. Use when the user asks for a docs canvas, documentation overview, architecture walkthrough, API reference page, or wants to render structured documentation as an interactive canvas."
---

> Claude Code compatibility: converted from Cursor plugin `docs-canvas` v0.1.0.
> Use the host's equivalent tool or subagent interface when the text names a Cursor-specific control.
> Never claim that an unavailable hook, MCP server, named agent, or Cursor service ran.
> Experimental: excluded from default installation until live host evaluation passes.
> When Cursor Canvas is unavailable, create a standalone HTML artifact with ordinary web technologies.

# Docs Canvas

Build a canvas that presents documentation — architecture notes, API references, design docs, runbooks, or codebase walkthroughs — as an interactive, navigable surface rather than as a flat markdown file.

> **Status:** placeholder. The skill structure is in place so the canvas
> welcome page can surface this plugin via the marketplace query, but the
> full skill body still needs to be written. Treat the steps below as a
> starting outline and refine as the docs canvas pattern matures.

## Prerequisites

If the Cursor Canvas SDK is available, read its `SKILL.md` and type declarations before using it. Otherwise, skip Cursor SDK calls and produce an equivalent standalone HTML artifact with ordinary HTML, CSS, and JavaScript.

## Gather the source material

Accept any of: a directory of markdown files, a single doc URL, an inline outline, or a question to answer from the codebase. Collect headings, code blocks, diagrams, and any cross-references between documents.

## Plan the canvas layout

Decide the top-level structure before writing any components. A docs canvas usually has:

1. **Overview** — A short summary card with the purpose of the doc, scope, and audience.
2. **Table of contents** — Navigable list of sections, ideally pinned or sticky so the reader can jump around.
3. **Body sections** — One section per logical unit (architecture, API, examples, gotchas). Each section can mix prose, code blocks, diagrams, and callouts.
4. **References** — Links to related docs, source files, RFCs, and external material.

## Render with canvas primitives

Prefer built-in canvas components over raw HTML:

- Use cards/sections to group related content visually.
- Use code blocks with syntax highlighting for snippets.
- Use diagrams (DAG layout, mermaid) for architecture.
- Use callouts for "Important", "Warning", "Note", "Deprecated".
- Use tables for API parameter lists and option matrices.

## Tone and content

Write reader-facing prose. Lead with the answer or the headline, then explain. Keep examples small and runnable. Cite source files with `code references` so readers can jump in.

## Be creative

The sections above are a floor, not a ceiling. The goal is the fastest possible path for the reader to understand the topic — so look at the source material in front of you and ask what representation would actually help. A diagram, a sequence chart, a side-by-side comparison, a decision tree, a glossary, a curated FAQ, a single large worked example — whatever fits.

## Experimental host contract

This converted Skill is experimental because its upstream workflow is still a placeholder.
It is excluded from default installation. Use it only when the user explicitly selects it,
and describe the result as an evaluation artifact rather than a production-ready canvas.

### Cursor Canvas example

Only when the active host actually exposes Cursor Canvas, read the installed Canvas SDK Skill
and type declarations, build the documented section/card components, and verify the rendered
canvas. Do not infer SDK availability from this text.

### Claude Code fallback example

Write one self-contained `docs-canvas.html` file in the requested project directory, then report its absolute path. Embed CSS, JavaScript, diagrams, and source citations in that file; do not claim that Cursor Canvas rendered it.

### Required smoke evaluation

Before reporting success, verify the produced artifact has all of the following:

1. navigation links whose fragment targets exist;
2. syntax-readable code blocks;
3. at least one diagram with an accessible label or text alternative;
4. cross-references that resolve to sections or cited source paths; and
5. one standalone output that does not require local package trees or external assets.

Use `references/smoke-example.html` as a structural baseline. Passing that static fixture is
not evidence that Claude Code or Cursor Canvas rendered a newly generated artifact; report live
rendering as unverified unless it was actually exercised.
