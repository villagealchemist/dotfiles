# 🪄 Alchemist's dotfiles

My opinionated macOS development environment, managed with [chezmoi](https://www.chezmoi.io/).

This is a personal setup, not a generic bootstrap script. It is public so friends and fellow engineers can borrow the useful pieces, see how I work, or fork the whole thing. Review the target state before applying it to your Mac.

## What is here

| Area | Highlights |
| --- | --- |
| zsh | PATH management, durable history, long-standing Git aliases, macOS helpers, development tools, and Keychain-backed credentials |
| Git | My public commit identity |
| iTerm2 | My `Alchemist` terminal profile as JSON |
| Commands | Human-authored scripts installed in `~/bin` |

The repository root is intentionally kept readable. `.chezmoiroot` points chezmoi at [`home/`](home), where the actual
home-directory source state lives; personal extras do not dominate the project front page.

## Before you apply anything

Fork the repository first if you intend to use it as your own dotfiles. At minimum, review these files:

| File | Personal assumption |
| --- | --- |
| `home/dot_gitconfig` | Contains my name and public email address. Replace both with yours. |
| `home/dot_zshrc` | Includes my aliases, `alchemist@village` prompt label, preferred applications, camera mount path, Keychain service names, and tool wrappers. |
| `home/dot_zprofile` | Prefers Apple Silicon Homebrew and adds optional paths for tools I use. Missing directories are skipped. |
| `home/alchemist.json` | An iTerm2 profile that must be imported manually. |

Inspect the rendered changes before applying:

```sh
chezmoi diff
```

## Requirements

The shell files require macOS and zsh. Chezmoi is the only installation dependency:

```sh
brew install chezmoi
```

Everything else is optional and guarded where practical. My setup makes use of Homebrew, VS Code, `bat`, GitHub CLI, `uv`, `asdf`, pnpm, SoX, iTerm2, Docker Desktop, Icon Forge, Codex, and Gemini when they are installed.

## Install

### My machines: one command

On a new personal Mac, this installs chezmoi, clones this repository, and applies the managed state:

```sh
sh -c "$(curl -fsLS https://get.chezmoi.io)" -- init --apply villagealchemist
```

That recreates the managed files; it does not restore Keychain values, sign in to applications, or install every app.

### Forks: inspect first

Initialize the source directory without applying it:

```sh
chezmoi init villagealchemist
chezmoi diff
```

Then apply only zsh after reviewing the diff:

```sh
chezmoi apply ~/.zprofile ~/.zshrc
exec zsh -l
```

If you forked the repository, replace `villagealchemist` with your GitHub username.

### Full setup

Only use the full apply after reviewing and personalizing the files listed above:

```sh
chezmoi init villagealchemist
chezmoi diff
chezmoi apply
```

I intentionally do not recommend `chezmoi init --apply` here. The full target state includes my Git identity and personal shell preferences.

## Personal commands

The three human-authored commands in `~/bin` are ordinary chezmoi-managed files:

| Command | Notes |
| --- | --- |
| `bundlecrypt` | Portable `tar` + GPG pack/unpack helper. Unpacking into an existing destination can replace files with matching names. |
| `getrektnerd` | macOS app-removal utility. It is intentionally powerful; inspect `getrektnerd --dry-run <app>` before a real run. |
| `mac-keys` | MacBook-specific built-in keyboard toggle; it is not intended for arbitrary hardware. |

Package-manager-owned commands, Python shims, and `uv` tool links remain in `~/.local/bin` and are recreated by their
installers instead of being copied into Git.

Use `binnew <name>` to create, edit, and add a new executable to chezmoi. `bineditfile <name>` edits the managed source
and reapplies it. `binstatus`, `binpull`, `binpush`, and `binlog` now operate through the shared dotfiles repository;
`binpush` therefore pushes the current dotfiles branch, not a separate nested `~/bin` repository.

## iTerm2 profile

Chezmoi places the profile at `~/alchemist.json`. Import it in iTerm2:

1. Open **Settings > Profiles**.
2. Open **Other Actions**.
3. Choose **Import JSON Profiles**.
4. Select `~/alchemist.json`.

Importing the file does not automatically make it the default profile.

## Optional personal extras

### Custom ICNS library

Chezmoi places the finished custom icons in `~/custom-icns`. Their lowercase kebab-case filename stems are normalized by
IconForge when matching installed applications. Editable artwork and historical variants live outside this repository.

Preview the complete library before changing Finder icon state:

```sh
iconforge apply --all "$HOME/custom-icns" --dry-run --verbose
```

IconForge deliberately skips applications that require authorization during a bulk run. Apply those icons individually
with the narrowly scoped authorization described by IconForge; do not elevate the whole CLI.

## Credentials

No credential values are stored here. Optional helpers read named items from macOS Keychain only when invoked.

Add or replace an item without putting it in shell history:

```sh
keychain_set OPENAI_API_KEY
keychain_set github.com
keychain_audit
```

Histories, private keys, application caches, generated state, `.env` files, and machine identifiers are not tracked.

## Validate changes

Before committing edits:

```sh
zsh -n ~/.zprofile
zsh -n ~/.zshrc
python3 -m json.tool ~/alchemist.json >/dev/null
chezmoi verify
```

## License

[MIT](LICENSE)
