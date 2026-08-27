# 🪄 Alchemist's dotfiles

My opinionated macOS development environment, managed with [chezmoi](https://www.chezmoi.io/).

This is a personal setup, not a generic bootstrap script. It is public so friends and fellow engineers can borrow the useful pieces, see how I work, or fork the whole thing. Review the target state before applying it to your Mac.

## What is here

| Area | Highlights |
| --- | --- |
| zsh | PATH management, durable history, long-standing Git aliases, macOS helpers, development tools, and Keychain-backed credentials |
| Git | My public commit identity |
| iTerm2 | My `Alchemist` terminal profile as JSON |

## Before you apply anything

Fork the repository first if you intend to use it as your own dotfiles. At minimum, review these files:

| File | Personal assumption |
| --- | --- |
| `dot_gitconfig` | Contains my name and public email address. Replace both with yours. |
| `dot_zshrc` | Includes my aliases, `alchemist@village` prompt label, preferred applications, camera mount path, Keychain service names, and tool wrappers. |
| `dot_zprofile` | Prefers Apple Silicon Homebrew and adds optional paths for Docker Desktop, Icon Forge, and other tools I use. Missing directories are skipped. |
| `alchemist.json` | An iTerm2 profile that must be imported manually. |

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

### Safest: adopt only the shell files

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

## iTerm2 profile

Chezmoi places the profile at `~/alchemist.json`. Import it in iTerm2:

1. Open **Settings > Profiles**.
2. Open **Other Actions**.
3. Choose **Import JSON Profiles**.
4. Select `~/alchemist.json`.

Importing the file does not automatically make it the default profile.

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
