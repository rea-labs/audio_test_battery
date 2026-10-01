# Migrating PROLACTIN Development to Claude Code (VS Code)
*From browser chat to IDE-integrated AI*

---

## What Is Claude Code

Claude Code is a CLI tool that runs Claude as an agentic coding assistant with direct access to your local file system, terminal, and git. The VS Code extension surfaces this in a sidebar panel. Unlike browser chat, Claude Code reads, edits, and executes files directly — no copy-paste.

---

## Pros vs Cons

### Pros
- **Full file access**: Claude reads entire project, not just what you paste. No more truncation.
- **Direct edits**: Claude edits files via `str_replace` — no "here's the full file" dumps.
- **Terminal access**: Can run tests, install packages, check errors — sees actual output.
- **Persistent context**: Files don't disappear between sessions (unlike browser chat temp files).
- **Git integration**: Can inspect diffs, commit history, staged changes.
- **Longer effective context**: Uses file access to avoid bloating the context window with full file contents.
- **Reproducible**: Changes are tracked by git, not lost in chat history.

### Cons
- **Setup friction**: Requires Node.js, CLI install, API key config — 30–60 min first-time.
- **No project knowledge**: The browser project knowledge base (your uploaded docs) doesn't transfer — you'd need to include reference docs in your repo or paste them in.
- **Different quota**: Uses API tokens directly; heavy sessions can be expensive at high usage.
- **No memory system**: The cross-chat user memory from browser doesn't exist in Claude Code.
- **No built-in GUI**: No artifact rendering, no present_files button — output is terminal + code.
- **Audio/display**: Can't actually hear stimuli or see plots it generates (still runs headlessly from its perspective).

---

## Setup

### Prerequisites
- Node.js ≥ 18 (check: `node --version`)
- VS Code installed
- Anthropic API key

### Install
```bash
npm install -g @anthropic-ai/claude-code
```

### Configure API key
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# Add to ~/.zshrc or ~/.bashrc to persist
```

### Launch
```bash
cd /path/to/prolactin
claude
```
Or use the VS Code extension: install "Claude Code" from the marketplace, then open the sidebar panel.

---

## Recommended Workflow for PROLACTIN

### Project structure
Keep a `CONTEXT.md` (or use `PROLACTIN_project_status.md`) at the project root. Start each session with:
```
/read PROLACTIN_project_status.md
```
Claude Code will then have the context it needs without you explaining history.

### Reference docs
Put the MultiThreshold manual, Lecluyse PDFs, and miro notes in a `docs/` folder in the repo. Claude Code can then read them directly:
```
Please read docs/MultiThreshold_manual.txt and check if our reversal detection matches section 3.2
```

### Typical session flow
1. Open VS Code with PROLACTIN project
2. Open Claude Code sidebar or terminal
3. `claude` → it reads project structure automatically
4. Tell it what you're working on; reference `PROLACTIN_project_status.md`
5. Claude edits files directly, you review diffs in VS Code
6. Run tests in integrated terminal, share output with Claude

### Git discipline
Commit before each Claude Code session. This lets you `git diff` to see exactly what Claude changed, and `git reset` if something goes wrong.

```bash
git add -A && git commit -m "pre-session checkpoint"
```

---

## Key Commands / Tips

| Command | What it does |
|---------|-------------|
| `/read <file>` | Load a file into context |
| `/memory` | View/edit persistent notes (replaces user memory) |
| `#<file>` | Reference a file inline in your message |
| `Ctrl+C` | Interrupt Claude mid-task |
| `/clear` | Clear context window (start fresh) |

### Effective prompting in Claude Code
- Be specific about files: "Edit `adaptive_paradigm.py`, function `check_trial_conds`, around line 654..."
- Use git to show context: "Here's `git diff adaptive_paradigm.py` — does the reversal logic look correct?"
- For multi-file changes: "Make the FM fix (event_gen.py + paradigm_fm.py) described in code_audit_2026-02-19.md section 1.3"
- Ask it to run tests: "Run `python tests/test_adaptive_logic.py` and fix any failures"

### Managing context window in Claude Code
- Claude Code uses file access to stay efficient — it reads files on demand rather than loading everything upfront
- If context gets large, use `/clear` and re-orient with `PROLACTIN_project_status.md`
- For very large tasks, break into sub-sessions with git commits between them

---

## What Doesn't Transfer from Browser

| Browser feature | Claude Code equivalent |
|----------------|----------------------|
| Project knowledge (uploaded docs) | Put docs in `docs/` folder in repo |
| User memory | `/memory` command (persistent notes) |
| File download button | Files are directly on disk |
| Artifact rendering | Open files in VS Code |
| Past chat search | Git log + grep through chat exports |

---

## Recommendation for PROLACTIN

Claude Code is well-suited for this project because:
- The codebase is large enough that copy-paste in browser chat is painful
- You need direct file edits (not full file regeneration)
- You want to run tests and see real output

**Suggested transition plan:**
1. Set up Claude Code locally (30 min)
2. Add `PROLACTIN_project_status.md` to repo root
3. Move reference docs to `docs/` folder
4. Use Claude Code for all code edits going forward
5. Use browser chat only for high-level planning / document generation

**One gotcha specific to PROLACTIN**: Claude Code can't hear audio or see tkinter windows. For stimulus validation (T6) and GUI testing (T8), you'll still need to run the code yourself and report results back. Everything else (logic, data format, CSV output) can be fully automated.
