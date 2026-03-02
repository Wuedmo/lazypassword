package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

var (
	titleStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#7D56F4"))
	itemStyle  = lipgloss.NewStyle().PaddingLeft(2)
	cursorStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#7D56F4")).Bold(true)
	selectedStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#04B575"))
	helpStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("#626262"))
	messageStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#04B575"))
)

func (m Model) renderUnlock() string {
	var b strings.Builder

	b.WriteString(titleStyle.Render("🔐 LazyPassword"))
	b.WriteString("\n\n")
	b.WriteString("Enter master password to unlock vault:\n\n")
	b.WriteString(m.unlockInput.View())
	b.WriteString("\n\n")
	b.WriteString(helpStyle.Render("Enter to submit • Esc or Ctrl+C to quit"))

	return b.String()
}

func (m Model) renderList() string {
	var b strings.Builder

	b.WriteString(titleStyle.Render("🔐 LazyPassword"))
	b.WriteString("\n\n")

	displayEntries := m.entries
	if m.searchQuery != "" {
		displayEntries = filterEntries(m.entries, m.searchQuery)
	}

	if len(displayEntries) == 0 {
		b.WriteString("No entries found.\n")
	} else {
		for i, entry := range displayEntries {
			cursor := "  "
			if m.cursor == i {
				cursor = cursorStyle.Render("> ")
			}
			line := fmt.Sprintf("%s%s (%s)", cursor, entry.Name, entry.Username)
			if m.cursor == i {
				line = selectedStyle.Render(line)
			} else {
				line = itemStyle.Render(line)
			}
			b.WriteString(line)
			b.WriteString("\n")
		}
	}

	if m.searchQuery != "" {
		b.WriteString(fmt.Sprintf("\nFilter: %s\n", m.searchQuery))
	}

	if m.message != "" {
		b.WriteString("\n")
		b.WriteString(messageStyle.Render(m.message))
		b.WriteString("\n")
	}

	b.WriteString("\n")
	b.WriteString(helpStyle.Render("j/k:nav • n:new • e:edit • d:delete • c:copy • /:search • q:quit"))

	return b.String()
}

func (m Model) renderAdd() string {
	var b strings.Builder

	b.WriteString(titleStyle.Render("➕ Add Entry"))
	b.WriteString("\n\n")

	b.WriteString("Name:\n")
	b.WriteString(m.nameInput.View())
	b.WriteString("\n\n")

	b.WriteString("Username:\n")
	b.WriteString(m.usernameInput.View())
	b.WriteString("\n\n")

	b.WriteString("Password:\n")
	b.WriteString(m.passwordInput.View())
	b.WriteString("\n\n")

	b.WriteString(helpStyle.Render("Tab:next • Enter:submit • Esc:cancel"))

	return b.String()
}

func (m Model) renderEdit() string {
	var b strings.Builder

	b.WriteString(titleStyle.Render("✏️  Edit Entry"))
	b.WriteString("\n\n")

	b.WriteString("Name:\n")
	b.WriteString(m.nameInput.View())
	b.WriteString("\n\n")

	b.WriteString("Username:\n")
	b.WriteString(m.usernameInput.View())
	b.WriteString("\n\n")

	b.WriteString("Password:\n")
	b.WriteString(m.passwordInput.View())
	b.WriteString("\n\n")

	b.WriteString(helpStyle.Render("Tab:next • Enter:submit • Esc:cancel"))

	return b.String()
}

func (m Model) renderDelete() string {
	var b strings.Builder

	b.WriteString(titleStyle.Render("🗑️  Delete Entry"))
	b.WriteString("\n\n")

	var entryName string
	for _, entry := range m.entries {
		if entry.ID == m.selectedID {
			entryName = entry.Name
			break
		}
	}

	b.WriteString(fmt.Sprintf("Are you sure you want to delete '%s'?\n\n", entryName))
	b.WriteString(helpStyle.Render("y:yes • n:no • Esc:cancel"))

	return b.String()
}

func (m Model) renderSearch() string {
	var b strings.Builder

	b.WriteString(titleStyle.Render("🔍 Search"))
	b.WriteString("\n\n")

	b.WriteString("Search query:\n")
	b.WriteString(m.searchInput.View())
	b.WriteString("\n\n")

	b.WriteString(helpStyle.Render("Enter:search • Esc:cancel"))

	return b.String()
}
