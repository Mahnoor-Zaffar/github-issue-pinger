# GitHub Issue Pinger

Track **open issues** from repos you've **forked** on GitHub — filtered by the last N days. Optional **SwiftBar** menu-bar widget + **HTML report** for the full list in the browser.

**Repo:** [github.com/sabasiddique1/github-issue-pinger](https://github.com/sabasiddique1/github-issue-pinger)

---

## What it does

- Fetches your **forked** repos via GitHub API
- By default uses **parent (upstream)** repos for issues (where issues actually live)
- Filters issues **opened in the last N days** (configurable, default 7)
- Outputs JSON; optional **HTML report** and **SwiftBar** dropdown

No scraping — GitHub REST API only.

---

## Requirements

- **Python 3.9+**
- **requests** (`pip install requests`)
- (Optional) **SwiftBar** on macOS for menu-bar widget — [SwiftBar](https://github.com/swiftbar/SwiftBar)

---

## Quick start

### 1. Clone & venv

```bash
git clone git@github.com:sabasiddique1/github-issue-pinger.git
cd github-issue-pinger
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install requests
```

### 2. Config

Copy or edit `github_issue_config.json`:

```json
{
  "github_username": "YOUR_GITHUB_USERNAME",
  "github_token": "",
  "include_prs": false,
  "max_issues_per_repo": 10,
  "max_repos": 50,
  "days_back": 7,
  "results_per_page": 100,
  "max_pages_per_repo": 3,
  "use_parent_issues": true,
  "max_display": 200
}
```

- **github_username** — Your GitHub username (required).
- **github_token** — Personal access token (recommended; avoids low rate limits). Create at GitHub → Settings → Developer settings → Personal access tokens. Scope: `public_repo` (or `repo` for private).
- **days_back** — Issues opened in the last N days (default 7).
- **use_parent_issues** — `true` = use parent/upstream repo for issues (recommended for forks).
- **max_display** — Max issues shown in SwiftBar dropdown and HTML report.

### 3. Run

```bash
python3 github_issue_pinger.py
```

Prints JSON (counts, per-repo breakdown, issue list). Also writes `github_issues_report.html` in the project folder.

---

## Outputs

| Output | Description |
|--------|-------------|
| **stdout** | JSON: `total_recent`, `per_repo_counts`, `items`, `html_report_path` |
| **github_issues_report.html** | Full list: date, repo, title; each row links to the issue |
| **github_issue_state.json** | Internal state (last-seen timestamps); safe to delete to reset |

---

## Optional: SwiftBar (macOS menu bar)

1. Install [SwiftBar](https://github.com/swiftbar/SwiftBar) (e.g. `brew install --cask swiftbar`).
2. **Edit** `github-issues.1h.py`: set `PYTHON` and `SCRIPT` to your clone path and venv:

   ```python
   BASE = "/path/to/your/github-issue-pinger"  # your clone path
   PYTHON = os.path.join(BASE, ".venv/bin/python3")
   SCRIPT = os.path.join(BASE, "github_issue_pinger.py")
   ```

   Replace `/path/to/your/github-issue-pinger` with the real path (e.g. `~/github-issue-pinger`).

3. Copy plugin into SwiftBar:

   ```bash
   cp github-issues.1h.py "$HOME/Library/Application Support/SwiftBar/Plugins/"
   chmod +x "$HOME/Library/Application Support/SwiftBar/Plugins/github-issues.1h.py"
   ```

4. Open SwiftBar and refresh: `open "swiftbar://refresh"`.

Menu bar shows e.g. **OSS Issues: 42 (last 7d)**. Click for dropdown: by-repo counts, recent issues (clickable), **Open full list (browser)** to open the HTML report.

---

## Optional: Open report in browser

After running the script:

```bash
open github_issues_report.html
```

Or from the SwiftBar dropdown: **Open full list (browser)** (if the script has been run at least once).

---

## Config reference

| Key | Default | Description |
|-----|---------|-------------|
| `github_username` | — | Your GitHub username |
| `github_token` | `""` | PAT (env `GITHUB_TOKEN` overrides) |
| `include_prs` | `false` | Include pull requests as issues |
| `max_issues_per_repo` | `10` | Legacy; pagination uses below |
| `max_repos` | `50` | Max forked repos to fetch |
| `days_back` | `7` | Only issues created in last N days |
| `results_per_page` | `100` | GitHub API per_page |
| `max_pages_per_repo` | `3` | Pages per repo for issue fetch |
| `use_parent_issues` | `true` | Use parent repo for issues (forks) |
| `max_display` | `200` | Max issues in dropdown/HTML |

---

## Environment overrides

- `GITHUB_ISSUE_CONFIG` — path to config JSON
- `GITHUB_ISSUE_STATE` — path to state JSON
- `GITHUB_ISSUE_HTML` — path to HTML report
- `GITHUB_TOKEN` — overrides `github_token` in config (recommended for security)

---

## Security

- Do **not** commit `github_issue_config.json` if it contains a token. Add it to `.gitignore` or use `GITHUB_TOKEN` only.
- Keep tokens with minimal scope (`public_repo` or `repo`).

---

## License

MIT (or your choice — add a LICENSE file).

---

## Contributing

PRs and issues welcome: [github.com/sabasiddique1/github-issue-pinger](https://github.com/sabasiddique1/github-issue-pinger).

