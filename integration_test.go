package main

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/wuedmo/lazypassword/crypto"
	"github.com/wuedmo/lazypassword/entry"
	"github.com/wuedmo/lazypassword/vault"
)

// TestFullWorkflow tests the complete vault workflow
func TestFullWorkflow(t *testing.T) {
	// Create temp directory
	tempDir := t.TempDir()
	vaultPath := filepath.Join(tempDir, "test.vault")
	
	password := "integration-test-password"
	
	// Step 1: Create vault
	t.Run("CreateVault", func(t *testing.T) {
		v := vault.NewVault(vaultPath)
		err := v.Create(password)
		if err != nil {
			t.Fatalf("Failed to create vault: %v", err)
		}
		
		if v.IsLocked() {
			t.Error("Vault should be unlocked after creation")
		}
		
		// Add some entries
		for i := 0; i < 3; i++ {
			e := entry.NewEntry()
			e.Title = "Entry " + string(rune('A'+i))
			e.Username = "user" + string(rune('1'+i))
			e.Password = "password" + string(rune('1'+i))
			v.AddEntry(e)
		}
		
		err = v.Save()
		if err != nil {
			t.Fatalf("Failed to save vault: %v", err)
		}
		
		v.Lock()
	})
	
	// Step 2: Unlock and verify
	t.Run("UnlockAndVerify", func(t *testing.T) {
		v := vault.NewVault(vaultPath)
		err := v.Unlock(password)
		if err != nil {
			t.Fatalf("Failed to unlock vault: %v", err)
		}
		
		entries := v.GetEntries()
		if len(entries) != 3 {
			t.Errorf("Expected 3 entries, got %d", len(entries))
		}
		
		// Verify entry data
		found := false
		for _, e := range entries {
			if e.Title == "Entry A" && e.Username == "user1" {
				found = true
				break
			}
		}
		if !found {
			t.Error("Entry A not found or data mismatch")
		}
	})
	
	// Step 3: Update entry
	t.Run("UpdateEntry", func(t *testing.T) {
		v := vault.NewVault(vaultPath)
		v.Unlock(password)
		
		entries := v.GetEntries()
		if len(entries) == 0 {
			t.Fatal("No entries to update")
		}
		
		entry := entries[0]
		originalTitle := entry.Title
		entry.Title = "Updated " + originalTitle
		
		err := v.UpdateEntry(entry.ID, entry)
		if err != nil {
			t.Fatalf("Failed to update entry: %v", err)
		}
		
		err = v.Save()
		if err != nil {
			t.Fatalf("Failed to save after update: %v", err)
		}
		
		// Verify update persisted
		v.Lock()
		v2 := vault.NewVault(vaultPath)
		v2.Unlock(password)
		
		entries = v2.GetEntries()
		found := false
		for _, e := range entries {
			if e.Title == "Updated "+originalTitle {
				found = true
				break
			}
		}
		if !found {
			t.Error("Updated entry not persisted")
		}
	})
	
	// Step 4: Delete entry
	t.Run("DeleteEntry", func(t *testing.T) {
		v := vault.NewVault(vaultPath)
		v.Unlock(password)
		
		entries := v.GetEntries()
		if len(entries) == 0 {
			t.Fatal("No entries to delete")
		}
		
		idToDelete := entries[0].ID
		originalCount := len(entries)
		
		err := v.DeleteEntry(idToDelete)
		if err != nil {
			t.Fatalf("Failed to delete entry: %v", err)
		}
		
		err = v.Save()
		if err != nil {
			t.Fatalf("Failed to save after delete: %v", err)
		}
		
		entries = v.GetEntries()
		if len(entries) != originalCount-1 {
			t.Errorf("Expected %d entries after delete, got %d", originalCount-1, len(entries))
		}
	})
	
	// Step 5: Wrong password should fail
	t.Run("WrongPassword", func(t *testing.T) {
		v := vault.NewVault(vaultPath)
		err := v.Unlock("wrong-password")
		if err == nil {
			t.Error("Unlock with wrong password should fail")
		}
		
		if !v.IsLocked() {
			t.Error("Vault should remain locked after failed unlock")
		}
	})
}

// TestCryptoRoundTrip tests encryption/decryption round trip
func TestCryptoRoundTrip(t *testing.T) {
	password := "test-password"
	salt := crypto.GenerateSalt()
	key := crypto.DeriveKey(password, salt)
	
	testData := []string{
		"short",
		"a longer string with spaces and special chars: !@#$%^&*()",
		"Unicode: 你好世界 🎉",
		"Very long data: " + string(make([]byte, 10000)),
	}
	
	for _, data := range testData {
		encrypted, err := crypto.Encrypt([]byte(data), key)
		if err != nil {
			t.Errorf("Encrypt failed for %q: %v", data[:min(20, len(data))], err)
			continue
		}
		
		decrypted, err := crypto.Decrypt(encrypted, key)
		if err != nil {
			t.Errorf("Decrypt failed for %q: %v", data[:min(20, len(data))], err)
			continue
		}
		
		if string(decrypted) != data {
			t.Errorf("Data mismatch for %q", data[:min(20, len(data))])
		}
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// TestConcurrentAccess tests that vault handles concurrent operations safely
func TestConcurrentAccess(t *testing.T) {
	// This is a placeholder for concurrent access tests
	// In production, you'd use sync.Mutex in the vault
	t.Skip("Concurrent access tests require mutex implementation")
}

// TestLargeVault tests performance with many entries
func TestLargeVault(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping large vault test in short mode")
	}
	
	tempDir := t.TempDir()
	vaultPath := filepath.Join(tempDir, "large.vault")
	password := "test-password"
	
	v := vault.NewVault(vaultPath)
	v.Create(password)
	
	// Add 1000 entries
	start := time.Now()
	for i := 0; i < 1000; i++ {
		e := entry.NewEntry()
		e.Title = "Entry " + string(rune(i))
		e.Username = "user" + string(rune(i))
		e.Password = "password" + string(rune(i))
		v.AddEntry(e)
	}
	
	err := v.Save()
	if err != nil {
		t.Fatalf("Failed to save large vault: %v", err)
	}
	
	saveTime := time.Since(start)
	t.Logf("Saved 1000 entries in %v", saveTime)
	
	// Unlock and verify
	v.Lock()
	v2 := vault.NewVault(vaultPath)
	
	start = time.Now()
	err = v2.Unlock(password)
	if err != nil {
		t.Fatalf("Failed to unlock large vault: %v", err)
	}
	unlockTime := time.Since(start)
	t.Logf("Unlocked vault with 1000 entries in %v", unlockTime)
	
	entries := v2.GetEntries()
	if len(entries) != 1000 {
		t.Errorf("Expected 1000 entries, got %d", len(entries))
	}
}

// TestVaultFilePermissions tests that vault files have correct permissions
func TestVaultFilePermissions(t *testing.T) {
	tempDir := t.TempDir()
	vaultPath := filepath.Join(tempDir, "test.vault")
	password := "test-password"
	
	v := vault.NewVault(vaultPath)
	v.Create(password)
	v.Save()
	
	info, err := os.Stat(vaultPath)
	if err != nil {
		t.Fatalf("Failed to stat vault file: %v", err)
	}
	
	mode := info.Mode().Perm()
	// Should be readable/writable by owner only (0600)
	if mode != 0600 {
		t.Errorf("Vault file permissions should be 0600, got %o", mode)
	}
}
