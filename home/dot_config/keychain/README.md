# Keychain helpers

The helpers load from `.zshrc` and are managed by chezmoi. Open a new terminal or reload:

```zsh
source ~/.zshrc
```

Search a remembered fragment across service names, labels, and accounts. Search ignores case and treats punctuation literally. Multiple words must all match the same item:

```zsh
kc orchid
kc search orchid production
```

Browse generic password entries saved for your macOS account, or include other accounts and internet-password entries:

```zsh
kc list
kc list --all
```

Search and listing show metadata only: type, service or server, account, label, and Keychain path. They use the accessible macOS Keychain search list. A failed scan reports an unknown status. No match does not prove an item is absent from locked, unlisted, or other credential stores.

Use an exact generic-password service name for these commands. Press Tab after the subcommand to complete saved service names:

```zsh
kc has 'EXACT_SERVICE_NAME'
kc copy 'EXACT_SERVICE_NAME'
kc get 'EXACT_SERVICE_NAME'
```

Copy places the secret on the clipboard without printing it. Get explicitly prints it. Both may trigger the normal macOS access prompt. The clipboard is not automatically cleared. An optional account and Keychain path select entries outside the defaults:

```zsh
kc has 'EXACT_SERVICE_NAME' 'ACCOUNT' '/path/to/custom.keychain-db'
```

Save or update a generic password using the native hidden prompt. The secret is not put into command arguments. Set writes to the default Keychain and optionally accepts an account. Native prompting replaces the previous shell read and its empty-value check:

```zsh
kc set 'EXACT_SERVICE_NAME'
kc set 'EXACT_SERVICE_NAME' 'ACCOUNT'
```

Delete requires an exact name and a typed confirmation in a terminal:

```zsh
kc delete 'EXACT_SERVICE_NAME'
```

The original credential-loading workflows remain available through their `use-*`, package-manager, Gemini, and `gh-token` commands. Audit lists saved entries without arguments; with names, it checks each exact service and returns failure when an item is missing or inaccessible:

```zsh
kc audit
kc audit OPENAI_API_KEY github.com
kc help
```

No passwords are loaded on shell startup. Discovery and completion do not request password data or cache the inventory. Python 3 and macOS's `security` command are required for discovery.

Run the offline regression checks from the chezmoi source repository:

```zsh
python3 -B tests/test_keychain.py
```
