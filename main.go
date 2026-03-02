package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"github.com/wuedmo/lazypassword/tui"

	tea "github.com/charmbracelet/bubbletea"
)

func main() {
	var vaultPath string
	flag.StringVar(&vaultPath, "vault", "", "Path to vault file")
	flag.Parse()

	if vaultPath == "" {
		homeDir, err := os.UserHomeDir()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error getting home directory: %v\n", err)
			os.Exit(1)
		}
		vaultPath = filepath.Join(homeDir, ".config", "lazypassword", "vault.lpv")
	}

	vaultDir := filepath.Dir(vaultPath)
	if err := os.MkdirAll(vaultDir, 0700); err != nil {
		fmt.Fprintf(os.Stderr, "Error creating vault directory: %v\n", err)
		os.Exit(1)
	}

	model := tui.New(vaultPath)

	p := tea.NewProgram(model, tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error running program: %v\n", err)
		os.Exit(1)
	}
}
