{{- define "unishield.name" -}}
unishield
{{- end }}

{{- define "unishield.fullname" -}}
{{ .Release.Name }}-unishield
{{- end }}

{{- define "unishield.labels" -}}
app.kubernetes.io/name: {{ include "unishield.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
