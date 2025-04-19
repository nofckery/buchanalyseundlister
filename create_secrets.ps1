# Projekt-ID setzen
$PROJECT_ID = "buchanalyse-prod"

# Funktion zum Erstellen eines Secrets
function Create-Secret {
    param (
        [string]$secretName,
        [string]$secretValue
    )
    
    Write-Host "Erstelle Secret: $secretName"
    
    # Erstelle Secret
    gcloud secrets create $secretName --replication-policy="automatic"
    
    # Füge Secret-Version hinzu
    $secretValue | gcloud secrets versions add $secretName --data-file=-
}

# Secrets aus .env-Datei erstellen
$envContent = Get-Content .env

foreach ($line in $envContent) {
    if ($line -match '^\s*([^#][^=]+)=(.+)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim(' "''')
        
        if ($key -and $value) {
            Create-Secret -secretName $key -secretValue $value
        }
    }
}

Write-Host "Secrets wurden erfolgreich erstellt!"