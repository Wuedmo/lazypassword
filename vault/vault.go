package vault

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/wuedmo/lazypassword/crypto"
	"github.com/wuedmo/lazypassword/entry"
)

// VaultData is the structure stored in the encrypted vault file
type VaultData struct {
	Entries []entry.Entry `json:"entries"`
}

// Vault manages the encrypted password vault
type Vault struct {
	path      string
	data      VaultData
	salt      []byte
	key       []byte
	locked    bool
	modified  bool
}

// NewVault creates a new vault instance (does not create file)
func NewVault(path string) *Vault {
	return &Vault{
		path:     path,
		data:     VaultData{Entries: []entry.Entry{}},
		salt:     nil,
		key:      nil,
		locked:   true,
		modified: false,
	}
}

// Create initializes a new vault file with the given password
// Creates: [salt:32][encrypted_vault_data]
func (v *Vault) Create(password string) error {
	if !v.locked {
		return fmt.Errorf("vault is already unlocked")
	}

	// Generate salt and derive key
	v.salt = crypto.GenerateSalt()
	v.key = crypto.DeriveKey(password, v.salt)

	// Initialize empty vault data
	v.data = VaultData{Entries: []entry.Entry{}}
	v.locked = false
	v.modified = true

	// Save to disk
	return v.Save()
}

// Unlock decrypts and loads the vault with the given password
func (v *Vault) Unlock(password string) error {
	if !v.locked {
		return fmt.Errorf("vault is already unlocked")
	}

	// Read vault file
	data, err := os.ReadFile(v.path)
	if err != nil {
		return fmt.Errorf("failed to read vault file: %w", err)
	}

	if len(data) < 32 {
		return fmt.Errorf("vault file too short")
	}

	// Extract salt and encrypted data
	v.salt = make([]byte, 32)
	copy(v.salt, data[:32])
	encryptedData := data[32:]

	// Derive key
	v.key = crypto.DeriveKey(password, v.salt)

	// Decrypt
	plaintext, err := crypto.Decrypt(encryptedData, v.key)
	if err != nil {
		// Wipe key on decryption failure
		crypto.SecureWipe(v.key)
		v.key = nil
		v.salt = nil
		return fmt.Errorf("failed to decrypt vault: %w", err)
	}

	// Parse JSON
	var vaultData VaultData
	if err := json.Unmarshal(plaintext, &vaultData); err != nil {
		crypto.SecureWipe(v.key)
		v.key = nil
		v.salt = nil
		return fmt.Errorf("failed to parse vault data: %w", err)
	}

	v.data = vaultData
	v.locked = false
	v.modified = false

	// Wipe plaintext from memory
	crypto.SecureWipe(plaintext)

	return nil
}

// Lock wipes decrypted data from memory
func (v *Vault) Lock() {
	if v.key != nil {
		crypto.SecureWipe(v.key)
		v.key = nil
	}
	if v.salt != nil {
		// Salt is not secret, but clear for hygiene
		v.salt = nil
	}
	v.data = VaultData{Entries: []entry.Entry{}}
	v.locked = true
	v.modified = false
}

// IsLocked returns true if the vault is currently locked
func (v *Vault) IsLocked() bool {
	return v.locked
}

// AddEntry adds a new entry to the vault
func (v *Vault) AddEntry(e entry.Entry) error {
	if v.locked {
		return fmt.Errorf("vault is locked")
	}

	// Check for duplicate ID
	for _, existing := range v.data.Entries {
		if existing.ID == e.ID {
			return fmt.Errorf("entry with ID %s already exists", e.ID)
		}
	}

	v.data.Entries = append(v.data.Entries, e)
	v.modified = true
	return nil
}

// UpdateEntry updates an existing entry by ID
func (v *Vault) UpdateEntry(id string, updated entry.Entry) error {
	if v.locked {
		return fmt.Errorf("vault is locked")
	}

	for i, e := range v.data.Entries {
		if e.ID == id {
			// Preserve creation timestamp
			updated.ID = id
			updated.CreatedAt = e.CreatedAt
			v.data.Entries[i] = updated
			v.modified = true
			return nil
		}
	}

	return fmt.Errorf("entry with ID %s not found", id)
}

// DeleteEntry removes an entry by ID
func (v *Vault) DeleteEntry(id string) error {
	if v.locked {
		return fmt.Errorf("vault is locked")
	}

	for i, e := range v.data.Entries {
		if e.ID == id {
			// Remove entry
			v.data.Entries = append(v.data.Entries[:i], v.data.Entries[i+1:]...)
			v.modified = true
			return nil
		}
	}

	return fmt.Errorf("entry with ID %s not found", id)
}

// GetEntries returns all entries (slice copy)
func (v *Vault) GetEntries() ([]entry.Entry, error) {
	if v.locked {
		return nil, fmt.Errorf("vault is locked")
	}

	// Return a copy to prevent external modification
	entries := make([]entry.Entry, len(v.data.Entries))
	copy(entries, v.data.Entries)
	return entries, nil
}

// Save encrypts and writes the vault atomically
func (v *Vault) Save() error {
	if v.locked {
		return fmt.Errorf("vault is locked")
	}

	if v.key == nil {
		return fmt.Errorf("no key available")
	}

	// Marshal vault data
	plaintext, err := json.Marshal(v.data)
	if err != nil {
		return fmt.Errorf("failed to marshal vault data: %w", err)
	}

	// Encrypt
	ciphertext, err := crypto.Encrypt(plaintext, v.key)
	if err != nil {
		return fmt.Errorf("failed to encrypt vault: %w", err)
	}

	// Build final data: [salt][ciphertext]
	data := make([]byte, 32+len(ciphertext))
	copy(data, v.salt)
	copy(data[32:], ciphertext)

	// Atomic write using temp file + rename
	dir := filepath.Dir(v.path)
	if err := os.MkdirAll(dir, 0700); err != nil {
		return fmt.Errorf("failed to create directory: %w", err)
	}

	tmpFile, err := os.CreateTemp(dir, ".lazypassword-*.tmp")
	if err != nil {
		return fmt.Errorf("failed to create temp file: %w", err)
	}

	tmpPath := tmpFile.Name()
	defer os.Remove(tmpPath)

	if _, err := tmpFile.Write(data); err != nil {
		tmpFile.Close()
		return fmt.Errorf("failed to write temp file: %w", err)
	}

	if err := tmpFile.Chmod(0600); err != nil {
		tmpFile.Close()
		return fmt.Errorf("failed to set permissions: %w", err)
	}

	if err := tmpFile.Close(); err != nil {
		return fmt.Errorf("failed to close temp file: %w", err)
	}

	// Atomic rename
	if err := os.Rename(tmpPath, v.path); err != nil {
		return fmt.Errorf("failed to rename temp file: %w", err)
	}

	v.modified = false

	// Wipe plaintext from memory
	crypto.SecureWipe(plaintext)

	return nil
}

// IsModified returns true if the vault has unsaved changes
func (v *Vault) IsModified() bool {
	return v.modified
}

// GetEntryByID returns a single entry by ID
func (v *Vault) GetEntryByID(id string) (*entry.Entry, error) {
	if v.locked {
		return nil, fmt.Errorf("vault is locked")
	}

	for _, e := range v.data.Entries {
		if e.ID == id {
			copy := e
			return &copy, nil
		}
	}

	return nil, fmt.Errorf("entry with ID %s not found", id)
}

// SearchEntries returns entries matching a query (case-insensitive)
func (v *Vault) SearchEntries(query string) ([]entry.Entry, error) {
	if v.locked {
		return nil, fmt.Errorf("vault is locked")
	}

	// Simple search - can be expanded
	queryLower := []byte(query)
	for i := range queryLower {
		if queryLower[i] >= 'A' && queryLower[i] <= 'Z' {
			queryLower[i] += 32
		}
	}

	var results []entry.Entry
	for _, e := range v.data.Entries {
		if containsIgnoreCase(e.Title, query) ||
			containsIgnoreCase(e.Username, query) ||
			containsIgnoreCase(e.URL, query) ||
			containsIgnoreCase(e.Notes, query) {
			results = append(results, e)
		}
	}

	return results, nil
}

func containsIgnoreCase(s, substr string) bool {
	if len(substr) == 0 {
		return true
	}
	if len(s) < len(substr) {
		return false
	}

	// Simple case-insensitive check
	lowerS := []byte(s)
	for i := range lowerS {
		if lowerS[i] >= 'A' && lowerS[i] <= 'Z' {
			lowerS[i] += 32
		}
	}

	lowerSubstr := []byte(substr)
	for i := range lowerSubstr {
		if lowerSubstr[i] >= 'A' && lowerSubstr[i] <= 'Z' {
			lowerSubstr[i] += 32
		}
	}

	// Simple contains
	sl, sub := string(lowerS), string(lowerSubstr)
	for i := 0; i <= len(sl)-len(sub); i++ {
		if sl[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}
