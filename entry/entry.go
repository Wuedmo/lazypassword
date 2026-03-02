package entry

import (
	"encoding/json"
	"time"

	"github.com/google/uuid"
)

// Entry represents a single password vault entry
type Entry struct {
	ID        string    `json:"id"`
	Title     string    `json:"title"`
	Username  string    `json:"username"`
	Password  string    `json:"password"`
	URL       string    `json:"url,omitempty"`
	Notes     string    `json:"notes,omitempty"`
	Tags      []string  `json:"tags,omitempty"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// MarshalJSON handles JSON serialization
func (e Entry) MarshalJSON() ([]byte, error) {
	type Alias Entry
	return json.Marshal(&struct {
		*Alias
		CreatedAt string `json:"created_at"`
		UpdatedAt string `json:"updated_at"`
	}{
		Alias:     (*Alias)(&e),
		CreatedAt: e.CreatedAt.Format(time.RFC3339),
		UpdatedAt: e.UpdatedAt.Format(time.RFC3339),
	})
}

// UnmarshalJSON handles JSON deserialization
func (e *Entry) UnmarshalJSON(data []byte) error {
	type Alias Entry
	aux := &struct {
		*Alias
		CreatedAt string `json:"created_at"`
		UpdatedAt string `json:"updated_at"`
	}{
		Alias: (*Alias)(e),
	}
	if err := json.Unmarshal(data, &aux); err != nil {
		return err
	}
	var err error
	e.CreatedAt, err = time.Parse(time.RFC3339, aux.CreatedAt)
	if err != nil {
		return err
	}
	e.UpdatedAt, err = time.Parse(time.RFC3339, aux.UpdatedAt)
	if err != nil {
		return err
	}
	return nil
}

// GenerateID creates a new UUID string
func GenerateID() string {
	return uuid.New().String()
}

// NewEntry creates a new entry with generated ID and timestamps
func NewEntry(title, username, password, url, notes string, tags []string) Entry {
	now := time.Now().UTC()
	return Entry{
		ID:        GenerateID(),
		Title:     title,
		Username:  username,
		Password:  password,
		URL:       url,
		Notes:     notes,
		Tags:      tags,
		CreatedAt: now,
		UpdatedAt: now,
	}
}

// UpdateTimestamps sets UpdatedAt to now
func (e *Entry) UpdateTimestamps() {
	e.UpdatedAt = time.Now().UTC()
}

// Update updates entry fields and timestamp
func (e *Entry) Update(title, username, password, url, notes string, tags []string) {
	e.Title = title
	e.Username = username
	e.Password = password
	e.URL = url
	e.Notes = notes
	e.Tags = tags
	e.UpdateTimestamps()
}
