package tui

import (
	"strings"

	"github.com/atotto/clipboard"
	tea "github.com/charmbracelet/bubbletea"
)

func (m Model) updateUnlocking(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.Type {
	case tea.KeyEnter:
		password := m.unlockInput.Value()
		if password != "" {
			m.vault.Password = password
			m.vault.Unlocked = true
			// TODO: Load entries from vault file
			m.entries = []Entry{
				{ID: "1", Name: "example.com", Username: "user@example.com", Password: "password123"},
			}
			m.state = StateList
			m.unlockInput.SetValue("")
		}
	case tea.KeyCtrlC, tea.KeyEsc:
		return m, tea.Quit
	}
	return m, nil
}

func (m Model) updateList(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "q", "ctrl+c":
		return m, tea.Quit
	case "j", "down":
		if m.cursor < len(m.entries)-1 {
			m.cursor++
		}
	case "k", "up":
		if m.cursor > 0 {
			m.cursor--
		}
	case "n":
		m.state = StateAdd
		m.nameInput.Focus()
		m.formFocus = 0
	case "e":
		if len(m.entries) > 0 && m.cursor < len(m.entries) {
			m.selectedID = m.entries[m.cursor].ID
			m.nameInput.SetValue(m.entries[m.cursor].Name)
			m.usernameInput.SetValue(m.entries[m.cursor].Username)
			m.passwordInput.SetValue(m.entries[m.cursor].Password)
			m.state = StateEdit
			m.formFocus = 0
			m.nameInput.Focus()
		}
	case "d":
		if len(m.entries) > 0 && m.cursor < len(m.entries) {
			m.selectedID = m.entries[m.cursor].ID
			m.state = StateDelete
		}
	case "c":
		if len(m.entries) > 0 && m.cursor < len(m.entries) {
			password := m.entries[m.cursor].Password
			clipboard.WriteAll(password)
			m.message = "Password copied to clipboard"
		}
	case "/":
		m.state = StateSearch
		m.searchInput.Focus()
	}
	return m, nil
}

func (m Model) updateAdd(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.Type {
	case tea.KeyEsc:
		m.resetForm()
		m.state = StateList
	case tea.KeyEnter:
		switch m.formFocus {
		case 0:
			m.formFocus = 1
			m.nameInput.Blur()
			m.usernameInput.Focus()
		case 1:
			m.formFocus = 2
			m.usernameInput.Blur()
			m.passwordInput.Focus()
		case 2:
			// Save entry
			entry := Entry{
				ID:       generateID(),
				Name:     m.nameInput.Value(),
				Username: m.usernameInput.Value(),
				Password: m.passwordInput.Value(),
			}
			m.entries = append(m.entries, entry)
			m.resetForm()
			m.state = StateList
		}
	case tea.KeyTab:
		m.formFocus = (m.formFocus + 1) % 3
		m.updateFormFocus()
	}
	return m, nil
}

func (m Model) updateEdit(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.Type {
	case tea.KeyEsc:
		m.resetForm()
		m.state = StateList
	case tea.KeyEnter:
		switch m.formFocus {
		case 0:
			m.formFocus = 1
			m.nameInput.Blur()
			m.usernameInput.Focus()
		case 1:
			m.formFocus = 2
			m.usernameInput.Blur()
			m.passwordInput.Focus()
		case 2:
			// Update entry
			for i, entry := range m.entries {
				if entry.ID == m.selectedID {
					m.entries[i].Name = m.nameInput.Value()
					m.entries[i].Username = m.usernameInput.Value()
					m.entries[i].Password = m.passwordInput.Value()
					break
				}
			}
			m.resetForm()
			m.state = StateList
		}
	case tea.KeyTab:
		m.formFocus = (m.formFocus + 1) % 3
		m.updateFormFocus()
	}
	return m, nil
}

func (m Model) updateDelete(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "y", "Y":
		// Delete entry
		for i, entry := range m.entries {
			if entry.ID == m.selectedID {
				m.entries = append(m.entries[:i], m.entries[i+1:]...)
				break
			}
		}
		if m.cursor >= len(m.entries) && m.cursor > 0 {
			m.cursor--
		}
		m.state = StateList
	case "n", "N", "esc":
		m.state = StateList
	}
	return m, nil
}

func (m Model) updateSearch(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.Type {
	case tea.KeyEsc:
		m.searchInput.SetValue("")
		m.state = StateList
	case tea.KeyEnter:
		m.searchQuery = m.searchInput.Value()
		m.state = StateList
	}
	return m, nil
}

func (m *Model) resetForm() {
	m.nameInput.SetValue("")
	m.usernameInput.SetValue("")
	m.passwordInput.SetValue("")
	m.nameInput.Blur()
	m.usernameInput.Blur()
	m.passwordInput.Blur()
	m.formFocus = 0
}

func (m *Model) updateFormFocus() {
	m.nameInput.Blur()
	m.usernameInput.Blur()
	m.passwordInput.Blur()
	switch m.formFocus {
	case 0:
		m.nameInput.Focus()
	case 1:
		m.usernameInput.Focus()
	case 2:
		m.passwordInput.Focus()
	}
}

func generateID() string {
	return "id_" + randomString(8)
}

func randomString(n int) string {
	const letters = "abcdefghijklmnopqrstuvwxyz0123456789"
	result := make([]byte, n)
	for i := range result {
		result[i] = letters[i%len(letters)]
	}
	return string(result)
}

func filterEntries(entries []Entry, query string) []Entry {
	if query == "" {
		return entries
	}
	var filtered []Entry
	lowerQuery := strings.ToLower(query)
	for _, entry := range entries {
		if strings.Contains(strings.ToLower(entry.Name), lowerQuery) ||
			strings.Contains(strings.ToLower(entry.Username), lowerQuery) {
			filtered = append(filtered, entry)
		}
	}
	return filtered
}
