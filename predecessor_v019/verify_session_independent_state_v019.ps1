param(
    [switch]$AllowPendingWorklog
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$AuditPath = Join-Path $Root 'seal_isv_edit0171_v019.py'
$ExpectedStateCanonicalSha256 = '81B8AD6C8BA681C5E0B6A646D41321CF3A8F9FB7B9861DF3E47DD2B040EEA598'
$ExpectedAuditBytes = 30971
$ExpectedAuditSha256 = '92030A3D866C7EC03F50EC357E8C2B92866F43983DAE1C1D265A77FDFA0A5BA9'

if (-not (Test-Path -LiteralPath $AuditPath -PathType Leaf)) {
    [Console]::Error.WriteLine("missing sealed audit engine: $AuditPath")
    exit 1
}
$AuditItem = Get-Item -LiteralPath $AuditPath
$AuditHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $AuditPath).Hash
if ($AuditItem.Length -ne $ExpectedAuditBytes -or $AuditHash -cne $ExpectedAuditSha256) {
    [Console]::Error.WriteLine("sealed audit-engine pin drift expected=$ExpectedAuditBytes/$ExpectedAuditSha256 actual=$($AuditItem.Length)/$AuditHash")
    exit 1
}

$Python = (Get-Command python.exe -ErrorAction Stop).Source
$Start = [System.Diagnostics.ProcessStartInfo]::new()
$Start.FileName = $Python
$Start.UseShellExecute = $false
$Start.RedirectStandardOutput = $true
$Start.RedirectStandardError = $true
$Start.CreateNoWindow = $true
$Start.StandardOutputEncoding = [System.Text.UTF8Encoding]::new($false)
$Start.StandardErrorEncoding = [System.Text.UTF8Encoding]::new($false)
[void]$Start.ArgumentList.Add('-B')
[void]$Start.ArgumentList.Add($AuditPath)
[void]$Start.ArgumentList.Add('--audit')
[void]$Start.ArgumentList.Add('--state-digest')
[void]$Start.ArgumentList.Add($ExpectedStateCanonicalSha256)
if ($AllowPendingWorklog) { [void]$Start.ArgumentList.Add('--allow-pending-worklog') }

$Process = [System.Diagnostics.Process]::new()
$Process.StartInfo = $Start
[void]$Process.Start()
$Stdout = $Process.StandardOutput.ReadToEnd()
$Stderr = $Process.StandardError.ReadToEnd()
$Process.WaitForExit()
if ($Process.ExitCode -ne 0 -or $Stderr.Length -ne 0) {
    if ($Stdout.Length -gt 0) { [Console]::Out.Write($Stdout) }
    if ($Stderr.Length -gt 0) { [Console]::Error.Write($Stderr) }
    if ($Process.ExitCode -eq 0) { exit 1 }
    exit $Process.ExitCode
}
[Console]::Out.Write($Stdout)
