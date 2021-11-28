package lib

import (
	"reflect"
	"testing"
	"time"
)

func init() {
	Now = func() time.Time { return time.Unix(int64(1638058435), int64(0)) }
	NewUuidString = func() string { return "edc65513-450e-4c87-908a-63dfc7628f20" }
}

func TestNewReporter(t *testing.T) {
	tests := []struct {
		name string
		want Reporter
	}{
		{
			name: "creates reporter with no vulnerabilities by default",
			want: Reporter{
				data: djavanReport{
					ScanDate:          Now().Unix(),
					ScanUuid:          NewUuidString(),
					ScanFormat:        "rhino-cloud-simple",
					ScanFormatVersion: 2.0,
					Platform:          "Any",
					Vulnerabilities:   map[string][]Finding{},
				},
		    },
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := NewReporter(); !reflect.DeepEqual(got, tt.want) {
				t.Errorf("NewReporter() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestReporter_Add(t *testing.T) {
	type args struct {
		vuln    string
		finding Finding
	}
	tests := []struct {
		name   string
		args   []args
		want  map[string][]Finding
	}{
		{
			name: "data is correct when called with one finding",
			args: []args{
				{
					vuln: "test_finding",
					finding: Finding{
						ResourceType:     "test_resource",
						GlobalIdentifier: "global_id",
						Name:             "name",
						MetaName:         "meta_name",
						Meta:             "meta",
					},
				},
			},
			want: map[string][]Finding{
				"test_finding": {
					Finding{
						ResourceType:     "test_resource",
						GlobalIdentifier: "global_id",
						Name:             "name",
						MetaName:         "meta_name",
						Meta:             "meta",
					},
				},
			},
		},
		{
			name: "data is correct when called with two of the same kind findings",
			args: []args{
				{
					vuln: "test_finding",
					finding: Finding{
						ResourceType:     "test_resource",
						GlobalIdentifier: "global_id",
						Name:             "name",
						MetaName:         "meta_name",
						Meta:             "meta",
					},
				},
				{
					vuln: "test_finding",
					finding: Finding{
						ResourceType:     "test_resource",
						GlobalIdentifier: "global_id2",
						Name:             "name2",
						MetaName:         "meta_name2",
						Meta:             "meta2",
					},
				},
			},
			want: map[string][]Finding{
				"test_finding": {
					Finding{
						ResourceType:     "test_resource",
						GlobalIdentifier: "global_id",
						Name:             "name",
						MetaName:         "meta_name",
						Meta:             "meta",
					},
					Finding{
						ResourceType:     "test_resource",
						GlobalIdentifier: "global_id2",
						Name:             "name2",
						MetaName:         "meta_name2",
						Meta:             "meta2",
					},
				},
			},
		},
		{
			name: "data is correct when called with two different kind of findings",
			args: []args{
				{
					vuln: "test_finding",
					finding: Finding{
						ResourceType:     "test_resource",
						GlobalIdentifier: "global_id",
						Name:             "name",
						MetaName:         "meta_name",
						Meta:             "meta",
					},
				},
				{
					vuln: "test_finding2",
					finding: Finding{
						ResourceType:     "test_resource",
						GlobalIdentifier: "global_id2",
						Name:             "name2",
						MetaName:         "meta_name2",
						Meta:             "meta2",
					},
				},
			},
			want: map[string][]Finding{
				"test_finding": {
					Finding{
						ResourceType:     "test_resource",
						GlobalIdentifier: "global_id",
						Name:             "name",
						MetaName:         "meta_name",
						Meta:             "meta",
					},
				},
				"test_finding2": {
					Finding{
						ResourceType:     "test_resource",
						GlobalIdentifier: "global_id2",
						Name:             "name2",
						MetaName:         "meta_name2",
						Meta:             "meta2",
					},
				},
			},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			r := NewReporter()
			for _, v := range tt.args {
				r.Add(v.vuln, v.finding)
			}
			if !reflect.DeepEqual(r.data.Vulnerabilities, tt.want) {
				t.Errorf("ToJson() got = %v, want %v", r.data.Vulnerabilities, tt.want)
			}
		})
	}
}

func TestReporter_ToJson(t *testing.T) {
	type fields struct {
		data djavanReport
	}
	tests := []struct {
		name    string
		fields  fields
		want    []byte
		wantErr bool
	}{
		{
			name:    "outputs report with no findings correctly",
			fields:  fields{
				data: djavanReport{
					ScanDate:          0,
					ScanUuid:          "",
					ScanFormat:        "",
					ScanFormatVersion: 0,
					Platform:          "",
					Vulnerabilities:   nil,
				},
			},
			want:    []byte(
				`{"scan-date":0,"scan-uuid":"","scan-format":"","scan-format-version":0,"platform":"",` +
				`"vulnerabilities":null}`,
		    ),
			wantErr: false,
		},
		{
			name:    "outputs report with one finding correctly",
			fields:  fields{
				data: djavanReport{
					ScanDate:          0,
					ScanUuid:          "",
					ScanFormat:        "",
					ScanFormatVersion: 0,
					Platform:          "",
					Vulnerabilities: map[string][]Finding{
						"test_finding": {
							Finding{
								ResourceType:     "test_resource",
								GlobalIdentifier: "global_id",
								Name:             "name",
								MetaName:         "meta_name",
								Meta:             "name",
							},
						},
					},
				},
			},
			want:    []byte(
				`{"scan-date":0,"scan-uuid":"","scan-format":"","scan-format-version":0,"platform":"",` +
				`"vulnerabilities":{"test_finding":[{"resource_type":"test_resource",` +
				`"global_identifier":"global_id","name":"name","meta_name":"meta_name","meta":"name"}]}}`,
			 ),
			wantErr: false,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			r := &Reporter{
				data: tt.fields.data,
			}
			got, err := r.ToJson()
			if (err != nil) != tt.wantErr {
				t.Errorf("ToJson() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("ToJson() got = %v, want %v", string(got), string(tt.want))
			}
		})
	}
}
