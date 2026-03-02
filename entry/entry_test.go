package entry

import (
	"encoding/json"
	"testing"
	"time"
)

func TestNewEntry(t *testing.T) {
	e := NewEntry()
	
	if e.ID == "" {
		t.Error("New entry should have generated ID")
	}
	
	if e.CreatedAt.IsZero() {
		t.Error("New entry should have CreatedAt timestamp")
	}
	
	if e.UpdatedAt.IsZero() {
		t.Error("New entry should have UpdatedAt timestamp")
	}
}

func TestEntryUpdate(t *testing.T) {
	e := NewEntry()
	time.Sleep(10 * time.Millisecond) // Ensure time difference
	
	oldUpdatedAt := e.UpdatedAt
	e.Title = "Test Title"
	e.Username = "testuser"
	e.Password = "secret123"
	e.Update()
	
	if e.Title != "Test Title" {
		t.Errorf("Title not set, got %s", e.Title)
	}
	
	if e.Username != "testuser" {
		t.Errorf("Username not set, got %s", e.Username)
	}
	
	if e.Password != "secret123" {
		t.Errorf("Password not set, got %s", e.Password)
	}
	
	if !e.UpdatedAt.After(oldUpdatedAt) {
		t.Error("UpdatedAt should be updated")
	}
}

func TestEntryJSON(t *testing.T) {
	e := NewEntry()
	e.Title = "GitHub"
	e.Username = "user"
	e.Password = "pass"
	e.URL = "https://github.com"
	e.Tags = []string{"dev", "git"}
	
	// Marshal
	data, err := json.Marshal(e)
	if err != nil {
		t.Fatalf("Marshal failed: %v", err)
	}
	
	// Unmarshal
	var e2 Entry
	err = json.Unmarshal(data, &e2)
	if err != nil {
		t.Fatalf("Unmarshal failed: %v", err)
	}
	
	if e2.Title != e.Title {
		t.Errorf("Title mismatch: %s vs %s", e2.Title, e.Title)
	}
	
	if e2.Username != e.Username {
		t.Errorf("Username mismatch: %s vs %s", e2.Username, e.Username)
	}
	
	if e2.Password != e.Password {
		t.Errorf("Password mismatch: %s vs %s", e2.Password, e.Password)
	}
	
	if e2.URL != e.URL {
		t.Errorf("URL mismatch: %s vs %s", e2.URL, e.URL)
	}
	
	if len(e2.Tags) != len(e.Tags) {
		t.Errorf("Tags length mismatch: %d vs %d", len(e2.Tags), len(e.Tags))
	}
}

func TestGenerateID(t *testing.T) {
	id1 := GenerateID()
	id2 := GenerateID()
	
	if id1 == "" {
		t.Error("Generated ID should not be empty")
	}
	
	if id1 == id2 {
		t.Error("Generated IDs should be unique")
	}
	
	if len(id1) != 36 {
		t.Errorf("UUID should be 36 characters, got %d", len(id1))
	}
}
