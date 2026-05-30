# Vault policies for UniShield — local dev configuration
path "secret/data/unishield/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/unishield/*" {
  capabilities = ["list", "read"]
}
