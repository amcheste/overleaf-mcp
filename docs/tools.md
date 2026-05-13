# Tools

Ten tools across read, write, structure, sync, and status. Every tool that takes a `project` argument also accepts omitting it when only one project is configured.

## Read

### `list_projects`

Lists all configured Overleaf project aliases with their display names.

**Inputs:** none.

### `list_files`

Lists files tracked in the project's local git clone.

**Inputs:**

- `project` (optional): project alias
- `extension` (optional): filter by extension, e.g. `tex` or `.tex`

### `read_file`

Reads a file from the project.

**Inputs:**

- `file_path` (required): path relative to the project root
- `project` (optional)

## Structure (LaTeX-aware)

### `get_sections`

Lists every LaTeX section in a `.tex` file with level + line range. Use this before `get_section_content` to discover what's available.

**Inputs:**

- `file_path` (required)
- `project` (optional)

### `get_section_content`

Returns the body of a named section, from its header line through the line before the next header at any level.

Errors loudly when the title isn't found (lists available titles) or matches multiple sections (forces disambiguation rather than silently picking one).

**Inputs:**

- `file_path` (required)
- `title` (required): exact, case-sensitive
- `project` (optional)

## Write

All write tools follow the same flow: pull latest from Overleaf → validate the path → make the change → commit → push back. On push failure the commit stays in the local cache.

### `edit_file`

Pulls latest, overwrites a file, commits, pushes to Overleaf. Short-circuits with `"No changes"` if the new content is identical to the existing.

**Inputs:**

- `file_path` (required)
- `content` (required): new full contents
- `project` (optional)

### `create_file`

Strict create. Errors with `FileExistsError` if the file already exists. Use `edit_file` to overwrite. Distinct intent so Claude can't accidentally clobber existing work.

**Inputs:**

- `file_path` (required)
- `content` (required)
- `project` (optional)

### `delete_file`

Pulls latest, removes the file, commits, pushes. Errors if the file doesn't exist (no silent no-ops).

**Inputs:**

- `file_path` (required)
- `project` (optional)

## Sync & status

### `sync`

Pulls the latest from Overleaf into the local clone. Reports whether HEAD moved.

**Inputs:**

- `project` (optional)

### `project_status`

One-shot summary: alias + display name, tracked file count, working-tree dirty state, and a one-line description of the last commit.

**Inputs:**

- `project` (optional)

---

For prompts that show how to combine these, see [Examples](examples.md).
