# 🔐 lazypassword

> A terminal-based password manager inspired by [LazyGit](https://github.com/jesseduffield/lazygit). Secure, keyboard-driven, and completely offline.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Security: AES-256-GCM](https://img.shields.io/badge/security-AES--256--GCM-green.svg)](https://en.wikipedia.org/wiki/Galois/Counter_Mode)

<p align="center">
  <img src="docs/screenshots/main.png" alt="lazypassword main interface with entries and git history" width="700">
</p>

---

## ✨ Features

### Core Security
- **🔐 Strong Encryption** — AES-256-GCM with Argon2id key derivation
- **🔑 Keyfile Support** — Optional additional authentication factor  
- **🔒 Plugin-based Encryption** — Choose from AES-256-GCM or ChaCha20-Poly1305
- **📵 100% Offline** — No cloud, no accounts, no tracking

### Password Management
- **📝 Multiple Entry Types** — Passwords, API keys, SSH keys, TOTP codes
- **🔍 Fast Search** — Live filtering as you type (`/`)
- **🏷️ Tagging** — Organize entries with custom tags
- **📋 Secure Clipboard** — Auto-clear after 30 seconds
- **🔒 Auto-Lock** — Locks after inactivity (configurable)

### Advanced Features
- **📜 Git Versioning** — Track all vault changes with built-in git history
- **🎨 Theming** — 7 built-in themes (dark, light, nord, dracula, monokai, solarized)
- **📤 Import/Export** — JSON format, compatible with Bitwarden and Chrome
- **🔐 API Key Storage** — Secure storage for OpenAI, AWS, Stripe, GitHub, and custom keys
- **🔑 SSH Key Management** — Generate, store, and export SSH keys
- **⏱️ TOTP/2FA** — Time-based one-time password generation

---

## 📦 Installation

### Requirements
- Python 3.8+
- Git (optional, for versioning)

### Install from Source

```bash
git clone https://github.com/Wuedmo/lazypassword.git
cd lazypassword
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Windows (WSL Recommended)

```powershell
wsl --install
# Inside WSL:
git clone https://github.com/Wuedmo/lazypassword.git
cd lazypassword
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

---

## 🚀 Quick Start

```bash
lazypassword              # Launch with default vault
lazypassword --vault /path/to/custom.vault  # Use custom location
lazypassword --help       # Show all options
```

### First Run

On first launch, you'll be prompted to create a master password (minimum 12 characters). You can optionally enable keyfile support for additional security.

<p align="center">
  <img src="docs/screenshots/unlock.png" alt="Unlock vault screen" width="500">
</p>

### Daily Usage

1. **Unlock** your vault with your master password
2. **Navigate** with vim keys (`j/k`, `gg`, `G`)
3. **Search** with `/`
4. **Add** entries with `n`
5. **Lock** with `l` or `q`

---

## ⌨️ Key Bindings

### Main Interface

| Key | Action |
|-----|--------|
| `j` / `k` | Navigate down / up |
| `gg` | Go to first entry |
| `G` | Go to last entry |
| `/` | Search / filter |
| `n` | **New** password entry |
| `e` | **Edit** entry |
| `d` | **Delete** entry |
| `c` | **Copy** password |
| `u` | **Copy** username |
| `y` | **Copy** to clipboard |

### Special Features

| Key | Action |
|-----|--------|
| `t` | **Theme** settings |
| `a` | **API Keys** management |
| `s` | **SSH Keys** management |
| `p` | **Encryption** settings |
| `Ctrl+i` | **Import** vault |
| `Ctrl+e` | **Export** vault |
| `v` | Toggle **history** panel |
| `g` | Show git **history** |

### System

| Key | Action |
|-----|--------|
| `l` | **Lock** vault |
| `h` | Show **help** |
| `q` | **Quit** |
| `Enter` | Confirm / Submit |
| `Esc` | Cancel / Back |

---

## 📸 Screenshots

### Main Interface
<p align="center">
  <img src="docs/screenshots/main.png" alt="Main interface" width="700">
</p>

### API Key Management
<p align="center">
  <img src="docs/screenshots/api-keys.png" alt="API Keys" width="600">
</p>

### SSH Key Management  
<p align="center">
  <img src="docs/screenshots/ssh-keys.png" alt="SSH Keys" width="600">
</p>

### Theme Selection
<p align="center">
  <img src="docs/screenshots/themes.png" alt="Themes" width="500">
</p>

---

## 🔒 Security Details

### Encryption
- **Algorithm:** AES-256-GCM (authenticated encryption)
- **Key Derivation:** Argon2id (memory-hard, slow)
- **Salt:** 32-byte random, unique per vault
- **IV:** 96-bit random per encryption

### Memory Safety
- Decrypted secrets exist in memory **only while unlocked**
- Memory is **securely wiped** on lock/exit
- No sensitive data in logs or core dumps

### File Storage
- Vault stored at: `~/.config/lazypassword/vault.lpv`
- Atomic writes (temp file + rename)
- Automatic backups before modification
- Git versioning for change history

---

## ⚙️ Configuration

### Environment Variables

```bash
export LAZYPASSWORD_VAULT_PATH=/path/to/vault.lpv  # Custom vault location
```

### Settings (stored in vault)

| Setting | Default | Description |
|---------|---------|-------------|
| `clipboard_timeout` | 30 | Seconds before clipboard clears |
| `auto_lock_minutes` | 10 | Minutes of inactivity before lock |
| `theme` | dark | UI theme name |
| `encryption_plugin` | aes-256-gcm | Encryption algorithm |

---

## 🛠️ Development

### Running Tests

```bash
pytest tests/ -v
```

### Project Structure

```
lazypassword/
├── lazypassword/
│   ├── __main__.py          # Entry point
│   ├── cli.py               # CLI arguments
│   ├── crypto.py            # Encryption utilities
│   ├── vault.py             # Vault management
│   ├── entry.py             # Password entry model
│   ├── api_key.py           # API key management
│   ├── ssh_manager.py       # SSH key management
│   ├── totp.py              # TOTP generation
│   ├── versioning.py        # Git-based versioning
│   ├── import_export.py     # Import/export functionality
│   ├── plugins/             # Encryption plugins
│   │   ├── base.py
│   │   ├── registry.py
│   │   └── builtins/
│   └── tui/                 # Terminal UI
│       ├── app.py
│       ├── screens.py
│       └── widgets.py
├── tests/
└── README.md
```

---

## 🗺️ Roadmap

### ✅ Completed
- [x] Core TUI with vim keybindings
- [x] AES-256-GCM encryption with Argon2id
- [x] Git versioning for vault history
- [x] 7 themes (dark, light, nord, dracula, monokai, solarized)
- [x] Keyfile support
- [x] TOTP/2FA support
- [x] JSON import/export (Bitwarden, Chrome compatible)
- [x] SSH key storage and management
- [x] API key storage (OpenAI, AWS, Stripe, GitHub, custom)
- [x] Plugin-based encryption (AES-256-GCM, ChaCha20-Poly1305)
- [x] Responsive design for all terminal sizes
- [x] Keyboard-only navigation (no mouse required)

### ⏳ Planned
- [ ] Plugin system for third-party extensions
- [ ] Remote sync (optional, encrypted) — postponed

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Credits

- Inspired by [LazyGit](https://github.com/jesseduffield/lazygit) by Jesse Duffield
- Built with [Textual](https://textual.textualize.io/)
- Crypto powered by [cryptography](https://cryptography.io/)

---

## ⚠️ Security Notice

**This software is provided as-is.** You are responsible for:
- Remembering your master password (no recovery possible)
- Backing up your vault file
- Securing your system

**No warranty, use at your own risk.**
