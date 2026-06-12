Add-Type -AssemblyName System.Runtime.WindowsRuntime
$vault = New-Object Windows.Security.Credentials.PasswordVault
try {
    $creds = $vault.FindAllByResource("git:https://github.com")
    foreach($c in $creds) {
        $c.RetrievePassword()
        Write-Output $c.Password
    }
} catch {
    Write-Output "ERROR: $_"
}
