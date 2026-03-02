# lazypassword (Go rewrite)

A terminal password manager for lazy people. Fast, simple, and stays out of your way.

## Installation

### Using go install

```bash
go install github.com/wuedmo/lazypassword@latest
```

### Download binary

Grab the latest binary from the [releases page](https://github.com/wuedmo/lazypassword/releases).

## Quick Start

```bash
# Create a new vault
lazypassword init

# Add an entry
lazypassword add github

# List entries
lazypassword list

# Copy password to clipboard
lazypassword copy github

# Interactive TUI mode
lazypassword
```

## Key Bindings

| Key | Action |
|-----|--------|
| `↑/k` | Move up |
| `↓/j` | Move down |
| `Enter` | Copy password to clipboard |
| `a` | Add new entry |
| `e` | Edit entry |
| `d` | Delete entry |
| `/` | Search/filter |
| `q` | Quit |

## Build

```bash
# Build binary
go build -o lazypassword

# Or use make
make build
```

## Differences from Python Version

| Feature | Python | Go |
|---------|--------|-----|
| Themes | Yes (configurable) | No (single style) |
| Distribution | pip install + deps | Single static binary |
| Startup time | ~1s | Instant |
| Dependencies | Python, click, cryptography, pyperclip | None (static) |

The Go version trades theming for simplicity and speed. One binary, zero dependencies, works everywhere.

## Roadmap

### ✅ Completed (Go rewrite)
- [x] Core crypto (AES-256-GCM, Argon2id)
- [x] Entry management (CRUD)
- [x] Vault with atomic writes
- [x] TUI with bubbletea
- [x] Vim keybindings (j/k, etc.)
- [x] Git versioning
- [x] Clipboard integration with auto-clear
- [x] Password generator
- [x] Search/filter

### ⏳ Next Up
- [ ] **Unit tests** — Test crypto, vault, and entry packages
- [ ] **Integration testing** — Test complete workflow end-to-end
- [ ] **Build & release** — Create release binaries for Linux, macOS, Windows
- [ ] **Repository cleanup** — Remove old Python code and unused libraries

### ⏳ Future (Post-cleanup)
- [ ] **Import/Export** — JSON import/export for migration
- [ ] **API Key storage** — Support for OpenAI, AWS, etc.
- [ ] **SSH Key management** — Generate and store SSH keys
- [ ] **TOTP/2FA** — Time-based one-time passwords

## License

MIT
