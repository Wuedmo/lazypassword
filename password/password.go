package password

import (
	"crypto/rand"
	"math/big"
)

const (
	lowercase   = "abcdefghijklmnopqrstuvwxyz"
	uppercase   = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
	numbers     = "0123456789"
	symbols     = "!@#$%^&*()_+-=[]{}|;:,.<>?"
	allChars    = lowercase + uppercase + numbers + symbols
)

// Generate creates a secure random password of the specified length
func Generate(length int) string {
	if length < 4 {
		length = 16 // Default length
	}

	// Ensure at least one of each character type
	result := make([]byte, length)

	// Pick one from each required set
	result[0] = randomChar(lowercase)
	result[1] = randomChar(uppercase)
	result[2] = randomChar(numbers)
	result[3] = randomChar(symbols)

	// Fill remaining with random from all sets
	for i := 4; i < length; i++ {
		result[i] = randomChar(allChars)
	}

	// Shuffle the result
	shuffle(result)

	return string(result)
}

// randomChar returns a random character from the given set
func randomChar(set string) byte {
	n, err := rand.Int(rand.Reader, big.NewInt(int64(len(set))))
	if err != nil {
		// Fallback (should never happen with crypto/rand)
		return set[0]
	}
	return set[n.Int64()]
}

// shuffle randomly shuffles a byte slice in place
func shuffle(data []byte) {
	for i := len(data) - 1; i > 0; i-- {
		n, err := rand.Int(rand.Reader, big.NewInt(int64(i+1)))
		if err != nil {
			continue
		}
		j := n.Int64()
		data[i], data[j] = data[j], data[i]
	}
}

// GenerateWithOptions creates a password with custom character sets
func GenerateWithOptions(length int, useLower, useUpper, useNumbers, useSymbols bool) string {
	if length < 4 {
		length = 16
	}

	var charset string
	if useLower {
		charset += lowercase
	}
	if useUpper {
		charset += uppercase
	}
	if useNumbers {
		charset += numbers
	}
	if useSymbols {
		charset += symbols
	}

	if charset == "" {
		charset = allChars
	}

	result := make([]byte, length)
	for i := 0; i < length; i++ {
		result[i] = randomChar(charset)
	}

	return string(result)
}

// GeneratePhrase creates a simple passphrase from words (memorable)
func GeneratePhrase(numWords int) string {
	if numWords < 3 {
		numWords = 4
	}

	// Simple word list for passphrase generation
	words := []string{
		"alpha", "bravo", "charlie", "delta", "echo", "foxtrot",
		"golf", "hotel", "india", "juliet", "kilo", "lima",
		"mike", "november", "oscar", "papa", "quebec", "romeo",
		"sierra", "tango", "uniform", "victor", "whiskey", "xray",
		"yankee", "zulu", "red", "blue", "green", "silver",
		"gold", "white", "black", "purple", "orange", "yellow",
	}

	result := make([]string, numWords)
	for i := 0; i < numWords; i++ {
		n, _ := rand.Int(rand.Reader, big.NewInt(int64(len(words))))
		result[i] = words[n.Int64()]
	}

	// Add a number at the end
	n, _ := rand.Int(rand.Reader, big.NewInt(1000))
	
	return joinStrings(result, "-") + n.String()
}

// joinStrings joins strings with separator
func joinStrings(strs []string, sep string) string {
	if len(strs) == 0 {
		return ""
	}
	result := strs[0]
	for i := 1; i < len(strs); i++ {
		result += sep + strs[i]
	}
	return result
}
