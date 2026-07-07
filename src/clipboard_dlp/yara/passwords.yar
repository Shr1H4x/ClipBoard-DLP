rule Password_Assignment
{
    meta:
        description = "Detect password/passwd/pwd assignment patterns"

    strings:
        $p1 = /\b(password|passwd|pwd)\s*[:=]\s*\S{4,}/ nocase

    condition:
        $p1
}

rule Secret_Assignment
{
    meta:
        description = "Detect secret/api key/token assignment patterns"

    strings:
        $s1 = /\b(secret|api[_-]?key|client[_-]?secret|access[_-]?token|auth[_-]?token)\s*[:=]\s*\S{4,}/ nocase

    condition:
        $s1
}

rule Env_Credential_Line
{
    meta:
        description = "Detect .env-style credential assignment lines"

    strings:
        $e1 = /(DB_PASSWORD|DATABASE_PASSWORD|SECRET_KEY|API_KEY|AWS_SECRET_ACCESS_KEY|PRIVATE_KEY)\s*=\s*\S+/ nocase

    condition:
        $e1
}

rule SSH_Password_Prompt_Context
{
    meta:
        description = "Detect copied SSH/login credential pairs (user + password on adjacent lines)"

    strings:
        $user = /\b(user(name)?|login)\s*[:=]\s*\S+/ nocase
        $pass = /\b(pass(word)?|pwd)\s*[:=]\s*\S+/ nocase

    condition:
        $user and $pass
}
