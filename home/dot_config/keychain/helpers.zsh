# Keychain discovery reads metadata only and runs on demand.

keychain-help() {
  cat <<'HELP'
Keychain helpers (also available as kc)

  keychain-search WORD [...] Search names, labels, and accounts, ignoring case
  keychain-search WORD [...] Shortcut: kc WORD
  keychain-list [WORD ...]  List generic passwords for your account
  keychain-list --all       Include other accounts and internet passwords
  keychain-has SERVICE [ACCOUNT] [KEYCHAIN] Check exact item without reading it
  keychain-get SERVICE [ACCOUNT] [KEYCHAIN] Print secret explicitly
  keychain-copy SERVICE [ACCOUNT] [KEYCHAIN] Copy secret to clipboard
  keychain-set SERVICE [ACCOUNT] Save/update using a hidden prompt
  keychain-delete SERVICE [ACCOUNT] [KEYCHAIN] Delete after confirmation
  keychain-audit [SERVICE ...] Check exact names, or list saved entries
  keychain-help             Show this guide

Search covers the accessible Keychain search list. It does not search Apple's
Passwords/iCloud store or unlock keychains. Discovery never reads secret values.
Internet results are for discovery; get/set/has/copy/delete use generic passwords.
Exact commands default to $USER. Quote names/accounts/paths containing spaces.
Use the ACCOUNT and KEYCHAIN columns to select entries outside the defaults.
Tab completes commands and saved generic service names. Credential loading
stays lazy; use-* helpers load values only when explicitly called.
HELP
}

keychain-inventory() {
  emulate -L zsh
  command python3 "$HOME/.config/keychain/inventory.py" "$@"
}

keychain-list() {
  keychain-inventory "$@"
}

keychain-search() {
  (( $# )) || { print -u2 -- 'usage: keychain-search <word> [word ...]'; return 2; }
  keychain-inventory --all -- "$@"
}

keychain-get() {
  emulate -L zsh
  unsetopt xtrace verbose
  (( $# >= 1 && $# <= 3 )) && [[ -n "$1" ]] || {
    print -u2 -- 'usage: keychain-get <service> [account] [keychain]'
    return 2
  }
  local -a keychainArgs=()
  (( $# == 3 )) && keychainArgs+=("$3")
  /usr/bin/security find-generic-password -a "${2-$USER}" -s "$1" -w "${keychainArgs[@]}"
}

keychain-has() {
  emulate -L zsh
  (( $# >= 1 && $# <= 3 )) && [[ -n "$1" ]] || {
    print -u2 -- 'usage: keychain-has <service> [account] [keychain]'
    return 2
  }
  local -a keychainArgs=()
  (( $# == 3 )) && keychainArgs+=("$3")
  local rc
  /usr/bin/security find-generic-password -a "${2-$USER}" -s "$1" "${keychainArgs[@]}" >/dev/null 2>&1
  rc=$?
  case $rc in
    0) print -r -- "$1: present" ;;
    44) print -r -- "$1: missing"; return 1 ;;
    *) print -ru2 -- "$1: Keychain lookup failed (exit $rc); status unknown"; return 2 ;;
  esac
}

keychain-set() {
  emulate -L zsh
  unsetopt xtrace verbose
  (( $# >= 1 && $# <= 2 )) && [[ -n "$1" ]] || {
    print -u2 -- 'usage: keychain-set <service> [account]'
    return 2
  }
  [[ -t 0 ]] || { print -u2 -- 'Run keychain-set in a terminal for the hidden password prompt.'; return 2; }
  # A final -w lets security prompt directly; the secret never becomes an argument.
  /usr/bin/security add-generic-password -U -a "${2-$USER}" -s "$1" -w || return $?
  print -r -- "Saved: $1 (account: ${2-$USER})"
}

keychain-copy() {
  emulate -L zsh
  unsetopt xtrace verbose
  local value
  value="$(keychain-get "$@")" || return $?
  print -rn -- "$value" | /usr/bin/pbcopy || return $?
  print -u2 -- 'Secret copied to the clipboard.'
}

keychain-delete() {
  emulate -L zsh
  (( $# >= 1 && $# <= 3 )) && [[ -n "$1" ]] || {
    print -u2 -- 'usage: keychain-delete <service> [account] [keychain]'
    return 2
  }
  [[ -t 0 ]] || { print -u2 -- 'Run keychain-delete in a terminal to confirm the exact item.'; return 2; }
  local reply
  local -a keychainArgs=()
  (( $# == 3 )) && keychainArgs+=("$3")
  print -ru2 -- "Delete generic password '$1' for account '${2-$USER}'?"
  print -nu2 -- 'Type yes to delete: '
  read -r reply || return 1
  [[ "$reply" == yes ]] || { print -u2 -- 'Cancelled.'; return 1; }
  /usr/bin/security delete-generic-password -a "${2-$USER}" -s "$1" "${keychainArgs[@]}"
}

keychain-audit() {
  emulate -L zsh
  (( $# )) || { keychain-list; return $?; }
  local service rc=0 itemRc
  for service in "$@"; do
    keychain-has "$service"
    itemRc=$?
    (( itemRc > rc )) && rc=$itemRc
  done
  return $rc
}

keychain() {
  emulate -L zsh
  local action="${1-help}"
  (( $# )) && shift
  case "$action" in
    help|-h|--help) keychain-help ;;
    list|ls) keychain-list "$@" ;;
    search|find) keychain-search "$@" ;;
    get) keychain-get "$@" ;;
    has) keychain-has "$@" ;;
    set) keychain-set "$@" ;;
    copy) keychain-copy "$@" ;;
    delete|rm) keychain-delete "$@" ;;
    audit) keychain-audit "$@" ;;
    *) keychain-search "$action" "$@" ;;
  esac
}

kc() { keychain "$@"; }

keychain-completion() {
  emulate -L zsh
  local -a names actions
  actions=(help list search get has set copy delete audit)
  if (( CURRENT == 2 )); then
    compadd -- "${actions[@]}"
    return
  fi
  case "${words[2]}" in
    get|has|set|copy|delete|rm|audit)
      if (( CURRENT == 3 )) || [[ "${words[2]}" == audit ]]; then
        names=("${(@f)$(keychain-inventory --names 2>/dev/null)}")
        (( ${#names} )) && compadd -- "${names[@]}"
      fi
      ;;
  esac
}

keychain-service-completion() {
  emulate -L zsh
  local -a names
  if (( CURRENT == 2 )) || [[ "${words[1]}" == keychain-audit ]]; then
    names=("${(@f)$(keychain-inventory --names 2>/dev/null)}")
    (( ${#names} )) && compadd -- "${names[@]}"
  fi
}

keychain-direct-completion() {
  emulate -L zsh
  local -a names
  names=("${(@f)$(keychain-inventory --names 2>/dev/null)}")
  (( ${#names} )) && compadd -- "${names[@]}"
}
