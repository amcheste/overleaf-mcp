# Examples

Concrete things people actually do with this server. The prompts below
work in any MCP-compatible client (Claude Desktop, Claude Code,
claude.ai web with the HTTP transport).

The pattern is the same across all of them: you describe what you want
in natural language, Claude picks the right tools and arguments, the
server does the work, and the change shows up in Overleaf within a few
seconds.

## 1. Tighten the introduction against the abstract

Useful when the abstract has been revised but the intro still has stale
framing.

> Read the abstract and the introduction in `main.tex` and tell me where
> the introduction's framing diverges from what the abstract promises.
> If you find drift, propose a tightened intro that lands the abstract's
> claims and rewrite the introduction in place.

What happens under the hood:
- `get_sections`: orient on what's in `main.tex`
- `get_section_content` × 2: pull the abstract and the introduction
- (Claude reasons + drafts)
- `edit_file`: write the tightened intro back, full pull → write →
  commit → push

The commit shows up in Overleaf with the message
`claude: edit main.tex`. Refresh the project, see the diff, accept or
revert in Overleaf's history view.

## 2. Add a new subsection in the right place

> Add a new subsection titled "Threat model" right after the "Related
> work" section in `main.tex`. Sketch the content as three paragraphs
> covering: assumptions about the deployment context, what we protect
> against, and what we explicitly don't.

What happens:
- `get_sections`: find the line range of "Related work" so the
  insertion point is right
- `read_file`: read the surrounding context to keep voice consistent
- `edit_file`: write `main.tex` with the new subsection inserted at
  the right line

## 3. What's in this project, and what's its current state?

Useful for context-setting when picking up a project after time away.

> Use the overleaf project_status and list_files tools, then summarise:
> how many files do I have, when was my last commit, what files are
> .tex vs .bib vs other, and what's the structure of `main.tex`?

What happens:
- `project_status`: file count, dirty state, last commit summary
- `list_files`: full file listing
- `get_sections` on `main.tex`: section structure

You get back a paragraph orienting you on the project: "You have 12
files (8 .tex, 2 .bib, 2 figures), last commit was 'add methodology
section' 3 days ago, and main.tex has 5 sections with subsections under
Method and Results."

## 4. Sync from Overleaf and find what changed

Useful when you've been editing in the Overleaf web UI and want Claude
to catch up before you continue working.

> Sync the project from Overleaf, then read `main.tex` and summarise
> what changed in the introduction since the previous version we
> discussed.

What happens:
- `sync`: pull latest from Overleaf, report whether HEAD moved
- `read_file`: current intro
- (Claude compares against what it had in conversation context)

Combine with `project_status` to see the new HEAD's commit message
("ah, you added the motivation paragraph in the web UI").

## Notes on prompting

- **Trust Claude to pick the tools.** You don't need to say "use
  `get_sections` first." Claude reads the tool list and picks
  appropriately. Telling it the *intent* works better than telling it
  the *steps*.
- **Be specific about what you want changed.** "Tighten the
  introduction" is vague; "tighten the introduction so it lands the
  abstract's claims about X and Y" gives Claude enough to do useful
  work.
- **Use `sync` at the start of a session** if you've been editing in
  Overleaf since the last time Claude touched the project. The
  `edit_file` tool always pulls before writing, but `sync` lets you
  *see* the changes before continuing.
- **Every change is a separate commit.** If Claude makes a mistake,
  `git revert` in Overleaf's history view (or your local clone) is one
  click.
