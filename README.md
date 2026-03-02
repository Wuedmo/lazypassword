# 🔒 lazypassword

> A terminal-based password manager inspired by [LazyGit](https://github.com/jesseduffield/lazygit). Fast, keyboard-driven, and completely offline.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Security: AES-256-GCM](https://img.shields.io/badge/security-AES--256--GCM-green.svg)](https://en.wikipedia.org/wiki/Galois/Counter_Mode)

---

## ✨ Features

- **🔐 Strong Encryption** — AES-256-GCM with Argon2id key derivation
- **🖥️ Beautiful TUI** — LazyGit-inspired terminal interface
- **⌨️ Keyboard-First** — Vim-style keybindings (`j/k`, `gg`, `/`)
- **📵 100% Offline** — No cloud, no accounts, no tracking
- **⏱️ Auto-Lock** — Locks after inactivity (configurable)
- **📋 Auto-Clear Clipboard** — Passwords clear from clipboard after 30s
- **🔑 Password Generator** — Built-in with configurable options
- **🔍 Fast Search** — Live filtering as you type
- **💾 Atomic Saves** — Crash-safe vault writes with backups

---

## 📦 Installation

### Linux / macOS

```bash
# Clone the repository
git clone https://github.com/Wuedmo/lazypassword.git
cd lazypassword

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .

# Or with poetry
poetry install
```

### Windows (WSL - Recommended)

lazypassword works best on Windows via WSL (Windows Subsystem for Linux):

```powershell
# Install WSL (if not already installed)
wsl --install

# Open WSL terminal, then:
git clone https://github.com/Wuedmo/lazypassword.git
cd lazypassword

python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Windows (Native - Experimental)

Native Windows support is experimental. Requires Windows Terminal for best experience:

```powershell
# Clone repository
git clone https://github.com/Wuedmo/lazypassword.git
cd lazypassword

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -e .

# Run
lazypassword
```

**Note:** Clipboard integration on native Windows requires `pywin32` (usually installed automatically with `pyperclip`).

### System Requirements

- Python 3.8+
- Linux, macOS, or Windows (WSL recommended)
- 64-bit OS recommended
- Terminal with Unicode support (Windows Terminal recommended on Windows)

---

## 🚀 Usage

### Launch

```bash
lazypassword                    # Launch with default vault
lazypassword --vault /path      # Use custom vault location
lazypassword --readonly         # Open in read-only mode
lazypassword --help             # Show help
```

### First Run

On first launch, you'll be prompted to create a **master password** (minimum 12 characters). This password encrypts your entire vault—**there is no recovery**.

```
┌─────────────────────────────────────┐
│  Welcome to lazypassword             │
│                                     │
│  No vault found. Create a new one.  │
│                                     │
│  Master password: ************       │
│  Confirm:         ************       │
│                                     │
└─────────────────────────────────────┘
```

### Unlocking

```
┌─────────────────────────────────────┐
│  Enter master password: ********    │
│                                     │
│  [5 attempts remaining]             │
└─────────────────────────────────────┘
```

---

## ⌨️ Key Bindings

| Key | Action |
|-----|--------|
| `j` / `k` | Move up/down |
| `gg` | Go to first entry |
| `G` | Go to last entry |
| `/` | Search/filter entries |
| `n` | **New** entry |
| `e` | **Edit** entry |
| `d` | **Delete** entry |
| `y` | **Copy** password |
| `Y` | **Copy** username |
| `c` | **Copy** to clipboard (generic) |
| `g` | **Generate** password |
| `?` | Toggle **help** |
| `l` / `Esc` | **Lock** vault |
| `q` | **Quit** |

### Navigation

- **hjkl** — Navigate (vim style)
- **Ctrl+d/u** — Half-page down/up
- **Enter** — Select/confirm
- **Esc** — Cancel/back

---

## 🏗️ Architecture

```
lazypassword/
├── lazypassword/
│   ├── __main__.py         # CLI entry point
│   ├── cli.py              # Argument parsing
│   ├── crypto.py           # AES-256-GCM + Argon2id
│   ├── vault.py            # Vault operations
│   ├── entry.py            # Entry data model
│   ├── tui/
│   │   ├── app.py          # Main TUI application
│   │   ├── screens.py      # UI screens
│   │   ├── widgets.py      # Custom widgets
│   │   └── keybindings.py  # Key definitions
│   └── utils/
│       ├── clipboard.py    # Cross-platform clipboard
│       └── password_gen.py # Password generator
├── tests/                   # Test suite
├── requirements.txt
└── setup.py
```

---

## 🔒 Security

### Encryption

- **Algorithm:** AES-256-GCM (authenticated encryption)
- **Key Derivation:** Argon2id (memory-hard, slow)
- **Salt:** 32-byte random, unique per vault
- **IV:** 96-bit random per encryption

### Memory Safety

- Decrypted secrets exist in memory **only while unlocked**
- Memory is **securely wiped** on lock/exit
- No sensitive data in logs
- No core dumps containing passwords

### Anti-Brute Force

- Configurable retry limits (default: 5)
- Exponential delay on failed attempts
- No timing hints for wrong passwords

### Data Resilience

- Atomic writes (temp file + rename)
- Automatic backups before modification
- Corruption detection and graceful failure

---

## 🛠️ Configuration

### Vault Location

Default: `~/.config/lazypassword/vault.lpv`

Override with environment variable:
```bash
export LAZYPASSWORD_VAULT_PATH=/path/to/vault.lpv
```

### Settings (stored in vault)

```json
{
  "clipboard_timeout": 30,      // seconds
  "auto_lock_minutes": 10,      // minutes of inactivity
  "max_retry_attempts": 5
}
```

---

## 🧪 Development

### Setup

```bash
git clone https://github.com/Wuedmo/lazypassword.git
cd lazypassword

python -m venv venv
source venv/bin/activate

pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/ -v
```

### Linting

```bash
flake8 lazypassword/
black lazypassword/
mypy lazypassword/
```

---

## 🗺️ Roadmap

- [x] v1.0 — Core TUI, encryption, CRUD
- [x] Git versioning for vault history
- [x] Theming (7 themes, persistent)
- [x] Keyfile support
- [x] TOTP/2FA support
- [x] JSON import/export
- [x] SSH key storage
- [x] **Encryption algorithm selection** — Plugin-based encryption with AES-256-GCM and ChaCha20-Poly1305
- [ ] **Responsive design** — Fix scrolling issues, optimize layout for different terminal sizes
- [ ] **Remove buttons** — Replace Submit/Cancel buttons with "Press ENTER/ESC" hints
- [ ] **API Key storage** — Support multiple formats (OpenAI, AWS, Stripe, custom headers, etc.)
- [ ] Plugin system
- [ ] Remote sync (optional, encrypted) — postponed
- [ ] Remote sync (optional, encrypted) — postponed

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Credits

- Inspired by [LazyGit](https://github.com/jesseduffield/lazygit) by Jesse Duffield
- Built with [Textual](https://textual.textualize.io/)
- Crypto powered by [cryptography](https://cryptography.io/)

---

## ⚠️ Disclaimer

This software is provided as-is. You are responsible for:
- Remembering your master password (no recovery possible)
- Backing up your vault file
- Securing your system

**No warranty, use at your own risk.**

---

<p align="center">
  Made with ⚡ by <a href="https://github.com/Wuedmo">Wuedmo</a>
</p>
