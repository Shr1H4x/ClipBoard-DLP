rule API_Keys
{
    meta:
        description = "Detect API keys and secrets"

    strings:
        $aws = /AKIA[0-9A-Z]{16}/
        $google = /AIza[0-9A-Za-z\-_]{35}/
        $github = /ghp_[A-Za-z0-9]{36}/

    condition:
        any of them
}