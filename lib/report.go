package lib

import (
	"encoding/json"
	"fmt"
	"github.com/google/uuid"
	"time"
)

var (
	Now = time.Now
	NewUuidString = uuid.NewString
)

type Finding struct {
	ResourceType string `json:"resource_type"`
	GlobalIdentifier string `json:"global_identifier"`
	Name string `json:"name,omitempty"`
	MetaName string `json:"meta_name,omitempty"`
	Meta string `json:"meta,omitempty"`
}

type djavanReport struct {
	ScanDate int64 `json:"scan-date"`
	ScanUuid string `json:"scan-uuid"`
	ScanFormat string `json:"scan-format"`
	ScanFormatVersion float64 `json:"scan-format-version"`
	Platform string `json:"platform"`
	Vulnerabilities map[string][]Finding `json:"vulnerabilities"`
}

func NewReporter() Reporter {
	return Reporter{
		data: djavanReport{
			ScanDate: Now().Unix(),
			ScanUuid: NewUuidString(),
			ScanFormat: "rhino-cloud-simple",
			ScanFormatVersion: 2.0,
			Platform: "Any",
			Vulnerabilities: map[string][]Finding{},
		},
	}
}

type Reporter struct {
	data djavanReport
}

func (r *Reporter) Add(vuln string, finding Finding) {
	r.data.Vulnerabilities[vuln] = append(r.data.Vulnerabilities[vuln], finding)
}

func (r *Reporter) ToJson() ([]byte, error) {
	marshal, err := json.Marshal(r.data)
	if err != nil {
		return nil, fmt.Errorf("converting report to json: %w", err)
	}
	return marshal, nil
}
