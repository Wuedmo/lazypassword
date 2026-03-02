package clipboard

import (
	"fmt"
	"os"
	"runtime"
	"time"

	"github.com/atotto/clipboard"
)

// ClearTimer is the duration before auto-clearing clipboard
const ClearTimer = 30 * time.Second

// Copy copies text to the clipboard
func Copy(text string) error {
	return clipboard.WriteAll(text)
}

// Clear clears the clipboard
func Clear() error {
	return clipboard.WriteAll("")
}

// CopyWithTimeout copies text and clears it after the specified duration
func CopyWithTimeout(text string, duration time.Duration) error {
	if err := Copy(text); err != nil {
		return fmt.Errorf("failed to copy to clipboard: %w", err)
	}

	// Start goroutine to clear clipboard after timeout
	go func() {
		time.Sleep(duration)
		Clear()
	}()

	return nil
}

// IsAvailable checks if clipboard functionality is available
func IsAvailable() bool {
	return clipboard.Unsupported == false
}

// CopyWithNotification copies text and optionally shows a notification when cleared
func CopyWithNotification(text string, duration time.Duration, notifyFunc func()) error {
	if err := Copy(text); err != nil {
		return err
	}

	go func() {
		time.Sleep(duration)
		Clear()
		if notifyFunc != nil {
			notifyFunc()
		}
	}()

	return nil
}

// Platform returns the current platform
func Platform() string {
	switch runtime.GOOS {
	case "darwin":
		return "macos"
	case "windows":
		return "windows"
	case "linux":
		// Check for Wayland vs X11
		if os.Getenv("WAYLAND_DISPLAY") != "" {
			return "linux-wayland"
		}
		return "linux-x11"
	default:
		return runtime.GOOS
	}
}
