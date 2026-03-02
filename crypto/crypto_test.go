package crypto

import (
	"bytes"
	"testing"
)

func TestDeriveKey(t *testing.T) {
	password := "test-password-123"
	salt := GenerateSalt()
	
	key1 := DeriveKey(password, salt)
	key2 := DeriveKey(password, salt)
	
	if len(key1) != 32 {
		t.Errorf("Expected key length 32, got %d", len(key1))
	}
	
	if !bytes.Equal(key1, key2) {
		t.Error("Same password and salt should produce same key")
	}
	
	// Different salt should produce different key
	salt2 := GenerateSalt()
	key3 := DeriveKey(password, salt2)
	if bytes.Equal(key1, key3) {
		t.Error("Different salt should produce different key")
	}
}

func TestGenerateSalt(t *testing.T) {
	salt1 := GenerateSalt()
	salt2 := GenerateSalt()
	
	if len(salt1) != 32 {
		t.Errorf("Expected salt length 32, got %d", len(salt1))
	}
	
	if bytes.Equal(salt1, salt2) {
		t.Error("Generated salts should be unique")
	}
}

func TestEncryptDecrypt(t *testing.T) {
	password := "my-test-password"
	salt := GenerateSalt()
	key := DeriveKey(password, salt)
	
	plaintext := []byte("secret data that needs encryption")
	
	// Encrypt
	ciphertext, err := Encrypt(plaintext, key)
	if err != nil {
		t.Fatalf("Encrypt failed: %v", err)
	}
	
	if bytes.Equal(plaintext, ciphertext) {
		t.Error("Ciphertext should differ from plaintext")
	}
	
	// Decrypt
	decrypted, err := Decrypt(ciphertext, key)
	if err != nil {
		t.Fatalf("Decrypt failed: %v", err)
	}
	
	if !bytes.Equal(plaintext, decrypted) {
		t.Error("Decrypted data should match original plaintext")
	}
	
	// Wrong key should fail
	wrongKey := DeriveKey("wrong-password", salt)
	_, err = Decrypt(ciphertext, wrongKey)
	if err == nil {
		t.Error("Decrypt with wrong key should fail")
	}
}

func TestSecureWipe(t *testing.T) {
	data := []byte("sensitive data that must be wiped")
	original := make([]byte, len(data))
	copy(original, data)
	
	SecureWipe(data)
	
	// Check that data is zeroed
	for i, b := range data {
		if b != 0 {
			t.Errorf("Byte %d not wiped, got %d", i, b)
		}
	}
	
	// Original copy should still have data
	if !bytes.Equal(original, []byte("sensitive data that must be wiped")) {
		t.Error("Original copy should be unaffected")
	}
}
