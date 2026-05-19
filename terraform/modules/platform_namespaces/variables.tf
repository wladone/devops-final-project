variable "namespaces" {
  description = "Namespaces to create and manage."
  type = map(object({
    labels      = map(string)
    annotations = map(string)
    hard        = map(string)
  }))
}
