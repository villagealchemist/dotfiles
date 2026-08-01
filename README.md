# 🪄 Alchemist's dotfiles

My opinionated, reproducible macOS development environment, managed with [chezmoi](https://www.chezmoi.io/).

This repository currently covers my zsh environment, Git identity, iTerm2 profile, and an automatic Karabiner setup that responds to my DisplayLink desk dock.

## What is included

| Area | Highlights |
| --- | --- |
| zsh | PATH management, shell history, Git shortcuts, macOS helpers, development tools, and Keychain-backed credentials |
| Git | Public user identity |
| iTerm2 | My `Alchemist` terminal profile |
| Karabiner-Elements | Automatic built-in keyboard behavior for an MX Keys Mini and Dell D6000 DisplayLink dock |
| launchd | A lightweight five-second watcher that switches Karabiner profiles when the dock connects or disconnects |

## Install

Review the repository before applying someone else's dotfiles to your machine.

```sh
brew install chezmoi
chezmoi init villagealchemist
chezmoi diff
chezmoi apply
```

On a machine where you are comfortable applying everything immediately:

```sh
chezmoi init --apply villagealchemist
```

## Keyboard automation

The keyboard helper chooses between two Karabiner profiles:

- `Desk - MX Keys Mini`: disables the MacBook typing keyboard while the MX Keys Mini is connected.
- `Mobile - Both Keyboards`: keeps the built-in and external keyboards available.

In automatic mode, connecting the Dell D6000 DisplayLink dock selects Desk mode. Disconnecting it selects Mobile mode. If the MX Keys Mini is unavailable, Karabiner leaves the built-in keyboard active. Touch ID remains available because it is handled separately from ordinary keyboard input.

Manual controls:

```sh
keyboard-mode status
keyboard-mode auto
keyboard-mode both
keyboard-mode desk
keyboard-mode toggle
```

The Karabiner configuration is managed as a chezmoi `create_` file. Karabiner rewrites the selected-profile state at runtime, so chezmoi installs the initial configuration without treating normal profile switches as permanent dotfile changes.

## Secrets and local state

No credentials are stored in this repository. Shell helpers retrieve optional credentials from macOS Keychain only when needed. Application caches, histories, private keys, machine identifiers, and generated state are intentionally excluded.

Some settings are specific to my hardware and workflow. Fork freely, review the device identifiers, and make the setup yours.

## License

[MIT](LICENSE)
