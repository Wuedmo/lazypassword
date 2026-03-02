package tui

import (
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
)

type State int

const (
	StateUnlocking State = iota
	StateList
	StateAdd
	StateEdit
	StateDelete
	StateSearch
)

type Entry struct {
	ID       string
	Name     string
	Username string
	Password string
}

type Vault struct {
	Path     string
	Unlocked bool
	Password string
	Entries  []Entry
}

type Model struct {
	state State
	vault Vault
	width int
	height int

	// Navigation
	cursor      int
	selectedID  string
	entries     []Entry
	filteredEntries []Entry

	// Search
	searchQuery string
	searchInput textinput.Model

	// Form fields
	nameInput     textinput.Model
	usernameInput textinput.Model
	passwordInput textinput.Model
	formFocus     int

	// Unlock
	unlockInput textinput.Model

	// Messages
	message string
}

func New(vaultPath string) Model {
	ui := textinput.New()
	ui.EchoMode = textinput.EchoPassword
	ui.Placeholder = "Master password"
	ui.Focus()

	si := textinput.New()
	si.Placeholder = "Search..."
	si.Focus()

	ni := textinput.New()
	ni.Placeholder = "Name"

	uiName := textinput.New()
	uiName.Placeholder = "Username"

	pi := textinput.New()
	pi.EchoMode = textinput.EchoPassword
	pi.Placeholder = "Password"

	return Model{
		state:         StateUnlocking,
		vault:         Vault{Path: vaultPath},
		unlockInput:   ui,
		searchInput:   si,
		nameInput:     ni,
		usernameInput: uiName,
		passwordInput: pi,
		entries:       []Entry{},
	}
}

func (m Model) Init() tea.Cmd {
	return textinput.Blink
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		return m, nil

	case tea.KeyMsg:
		switch m.state {
		case StateUnlocking:
			return m.updateUnlocking(msg)
		case StateList:
			return m.updateList(msg)
		case StateAdd:
			return m.updateAdd(msg)
		case StateEdit:
			return m.updateEdit(msg)
		case StateDelete:
			return m.updateDelete(msg)
		case StateSearch:
			return m.updateSearch(msg)
		}
	}

	// Update inputs
	var cmd tea.Cmd
	m.unlockInput, cmd = m.unlockInput.Update(msg)
	cmds = append(cmds, cmd)
	m.searchInput, cmd = m.searchInput.Update(msg)
	cmds = append(cmds, cmd)
	m.nameInput, cmd = m.nameInput.Update(msg)
	cmds = append(cmds, cmd)
	m.usernameInput, cmd = m.usernameInput.Update(msg)
	cmds = append(cmds, cmd)
	m.passwordInput, cmd = m.passwordInput.Update(msg)
	cmds = append(cmds, cmd)

	return m, tea.Batch(cmds...)
}

func (m Model) View() string {
	switch m.state {
	case StateUnlocking:
		return m.renderUnlock()
	case StateList:
		return m.renderList()
	case StateAdd:
		return m.renderAdd()
	case StateEdit:
		return m.renderEdit()
	case StateDelete:
		return m.renderDelete()
	case StateSearch:
		return m.renderSearch()
	default:
		return "Unknown state"
	}
}
