package versioning

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// Commit represents a git commit
type Commit struct {
	Hash    string
	Date    time.Time
	Message string
}

// Versioning handles git operations for the vault
type Versioning struct {
	vaultPath string
}

// New creates a new Versioning instance
func New(vaultPath string) *Versioning {
	return &Versioning{vaultPath: vaultPath}
}

// Init initializes a git repository in the vault directory
func (v *Versioning) Init() error {
	vaultDir := filepath.Dir(v.vaultPath)

	// Check if git is already initialized
	gitDir := filepath.Join(vaultDir, ".git")
	if _, err := os.Stat(gitDir); err == nil {
		return nil // Already initialized
	}

	// Initialize git repo
	cmd := exec.Command("git", "init")
	cmd.Dir = vaultDir
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to init git: %w", err)
	}

	// Set default user config if not present
	exec.Command("git", "config", "user.email", "lazypassword@local").Run()
	exec.Command("git", "config", "user.name", "LazyPassword").Run()

	return nil
}

// Commit creates a git commit with the given message
func (v *Versioning) Commit(message string) error {
	vaultDir := filepath.Dir(v.vaultPath)

	// Add the vault file
	cmd := exec.Command("git", "add", filepath.Base(v.vaultPath))
	cmd.Dir = vaultDir
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to add file: %w", err)
	}

	// Commit
	cmd = exec.Command("git", "commit", "-m", message)
	cmd.Dir = vaultDir
	if err := cmd.Run(); err != nil {
		// Ignore "nothing to commit" errors
		return nil
	}

	return nil
}

// History returns the git log with optional limit
func (v *Versioning) History(limit int) ([]Commit, error) {
	vaultDir := filepath.Dir(v.vaultPath)

	format := "%H|%ci|%s"
	cmd := exec.Command("git", "log", fmt.Sprintf("--pretty=format:%s", format), "-n", fmt.Sprintf("%d", limit))
	cmd.Dir = vaultDir

	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("failed to get history: %w", err)
	}

	lines := strings.Split(string(output), "\n")
	var commits []Commit

	for _, line := range lines {
		if line == "" {
			continue
		}

		parts := strings.SplitN(line, "|", 3)
		if len(parts) < 3 {
			continue
		}

		date, _ := time.Parse("2006-01-02 15:04:05 -0700", parts[1])
		commits = append(commits, Commit{
			Hash:    parts[0],
			Date:    date,
			Message: parts[2],
		})
	}

	return commits, nil
}

// Rollback restores the vault to a specific commit
func (v *Versioning) Rollback(commitHash string) error {
	vaultDir := filepath.Dir(v.vaultPath)

	cmd := exec.Command("git", "checkout", commitHash, "--", filepath.Base(v.vaultPath))
	cmd.Dir = vaultDir
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to rollback: %w", err)
	}

	return nil
}
