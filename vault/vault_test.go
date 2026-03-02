package vault

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/wuedmo/lazypassword/entry"
)

func TestNewVault(t *testing.T) {
	path := filepath.Join(t.TempDir(), "test.vault")
	v := NewVault(path)
	
	if v.path != path {
		t.Errorf("Path mismatch: %s vs %s", v.path, path)
	}
	
	if !v.IsLocked() {
		t.Error("New vault should be locked")
	}
}

func TestVaultCreateAndUnlock(t *testing.T) {
	path := filepath.Join(t.TempDir(), "test.vault")
	v := NewVault(path)
	
	password := "test-password-123"
	
	// Create
	err := v.Create(password)
	if err != nil {
		t.Fatalf("Create failed: %v", err)
	}
	
	if v.IsLocked() {
		t.Error("Vault should be unlocked after create")
	}
	
	// Check file exists
	if _, err := os.Stat(path); os.IsNotExist(err) {
		t.Error("Vault file should exist after create")
	}
	
	// Lock and unlock
	v.Lock()
	if !v.IsLocked() {
		t.Error("Vault should be locked after Lock()")
	}
	
	v2 := NewVault(path)
	err = v2.Unlock(password)
	if err != nil {
		t.Fatalf("Unlock failed: %v", err)
	}
	
	if v2.IsLocked() {
		t.Error("Vault should be unlocked after successful unlock")
	}
}

func TestVaultWrongPassword(t *testing.T) {
	path := filepath.Join(t.TempDir(), "test.vault")
	v := NewVault(path)
	
	v.Create("correct-password")
	v.Lock()
	
	v2 := NewVault(path)
	err := v2.Unlock("wrong-password")
	if err == nil {
		t.Error("Unlock with wrong password should fail")
	}
	
	if !v2.IsLocked() {
		t.Error("Vault should remain locked after failed unlock")
	}
}

func TestVaultAddAndGetEntries(t *testing.T) {
	path := filepath.Join(t.TempDir(), "test.vault")
	v := NewVault(path)
	v.Create("password")
	
	// Add entries
	e1 := entry.NewEntry()
	e1.Title = "GitHub"
	e1.Username = "user1"
	v.AddEntry(e1)
	
	e2 := entry.NewEntry()
	e2.Title = "Gmail"
	e2.Username = "user2"
	v.AddEntry(e2)
	
	// Save and reload
	err := v.Save()
	if err != nil {
		t.Fatalf("Save failed: %v", err)
	}
	
	v.Lock()
	
	v2 := NewVault(path)
	err = v2.Unlock("password")
	if err != nil {
		t.Fatalf("Unlock failed: %v", err)
	}
	
	entries := v2.GetEntries()
	if len(entries) != 2 {
		t.Errorf("Expected 2 entries, got %d", len(entries))
	}
	
	// Check entries
	found := false
	for _, e := range entries {
		if e.Title == "GitHub" && e.Username == "user1" {
			found = true
			break
		}
	}
	if !found {
		t.Error("GitHub entry not found")
	}
}

func TestVaultDeleteEntry(t *testing.T) {
	path := filepath.Join(t.TempDir(), "test.vault")
	v := NewVault(path)
	v.Create("password")
	
	e := entry.NewEntry()
	e.Title = "ToDelete"
	v.AddEntry(e)
	v.Save()
	
	entries := v.GetEntries()
	if len(entries) != 1 {
		t.Fatalf("Expected 1 entry, got %d", len(entries))
	}
	
	id := entries[0].ID
	err := v.DeleteEntry(id)
	if err != nil {
		t.Fatalf("DeleteEntry failed: %v", err)
	}
	
	entries = v.GetEntries()
	if len(entries) != 0 {
		t.Errorf("Expected 0 entries after delete, got %d", len(entries))
	}
}

func TestVaultUpdateEntry(t *testing.T) {
	path := filepath.Join(t.TempDir(), "test.vault")
	v := NewVault(path)
	v.Create("password")
	
	e := entry.NewEntry()
	e.Title = "Original"
	v.AddEntry(e)
	v.Save()
	
	entries := v.GetEntries()
	e2 := entries[0]
	e2.Title = "Updated"
	
	err := v.UpdateEntry(e2.ID, e2)
	if err != nil {
		t.Fatalf("UpdateEntry failed: %v", err)
	}
	
	entries = v.GetEntries()
	if entries[0].Title != "Updated" {
		t.Errorf("Title not updated, got %s", entries[0].Title)
	}
}
