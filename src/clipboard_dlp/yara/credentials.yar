rule Private_Key_Block
{
    meta:
        description = "Detect PEM-format private key blocks"

    strings:
        $rsa     = "-----BEGIN RSA PRIVATE KEY-----"
        $ec      = "-----BEGIN EC PRIVATE KEY-----"
        $generic = "-----BEGIN PRIVATE KEY-----"
        $openssh = "-----BEGIN OPENSSH PRIVATE KEY-----"
        $pgp     = "-----BEGIN PGP PRIVATE KEY BLOCK-----"

    condition:
        any of them
}

rule Slack_Token
{
    meta:
        description = "Detect Slack API tokens"

    strings:
        $slack = /xox[baprs]-[0-9A-Za-z-]{10,72}/

    condition:
        $slack
}

rule Generic_Bearer_Token
{
    meta:
        description = "Detect Authorization: Bearer style tokens"

    strings:
        $bearer = /[Bb]earer\s+[A-Za-z0-9\-_\.=]{16,}/

    condition:
        $bearer
}

rule DB_Connection_String
{
    meta:
        description = "Detect DB connection strings with embedded username:password"

    strings:
        $conn = /(postgres|postgresql|mysql|mongodb\+srv|mongodb|redis|amqp):\/\/[^\/\s:@]+:[^\/\s@]+@[^\/\s]+/ nocase

    condition:
        $conn
}

rule Basic_Auth_URL
{
    meta:
        description = "Detect URLs with embedded HTTP basic-auth credentials"

    strings:
        $url = /https?:\/\/[^\/\s:@]+:[^\/\s@]+@[^\/\s]+/ nocase

    condition:
        $url
}

rule Github_Token
{
    meta:
        description = "Detect GitHub personal/app access tokens"

    strings:
        $ghp = /ghp_[A-Za-z0-9]{36}/
        $gho = /gho_[A-Za-z0-9]{36}/
        $ghu = /ghu_[A-Za-z0-9]{36}/
        $ghs = /ghs_[A-Za-z0-9]{36}/
        $ghr = /ghr_[A-Za-z0-9]{36}/

    condition:
        any of them
}

rule Slack_Webhook
{
    meta:
        description = "Detect Slack incoming webhook URLs"

    strings:
        $hook = /https:\/\/hooks\.slack\.com\/services\/[A-Za-z0-9\/]{20,}/

    condition:
        $hook
}
