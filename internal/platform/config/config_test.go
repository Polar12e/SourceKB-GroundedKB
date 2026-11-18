package config

import "testing"

func TestPort(t *testing.T) {
	tests := []struct {
		name     string
		value    string
		fallback int
		want     int
		wantErr  bool
	}{
		{name: "unset uses fallback", value: "", fallback: 8080, want: 8080},
		{name: "valid override", value: "9090", fallback: 8080, want: 9090},
		{name: "not a number", value: "abc", fallback: 8080, wantErr: true},
		{name: "zero", value: "0", fallback: 8080, wantErr: true},
		{name: "too large", value: "65536", fallback: 8080, wantErr: true},
		{name: "negative", value: "-1", fallback: 8080, wantErr: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Setenv("TEST_PORT", tt.value)

			got, err := Port("TEST_PORT", tt.fallback)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("Port() error = nil, want error")
				}
				return
			}
			if err != nil {
				t.Fatalf("Port() error = %v", err)
			}
			if got != tt.want {
				t.Fatalf("Port() = %d, want %d", got, tt.want)
			}
		})
	}
}

func TestAddr(t *testing.T) {
	if got, want := Addr(8080), ":8080"; got != want {
		t.Fatalf("Addr(8080) = %q, want %q", got, want)
	}
}
