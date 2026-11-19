$serverScript = Join-Path $PSScriptRoot 'serve.py'
$launcher = Get-Command py.exe -ErrorAction SilentlyContinue
if ($launcher) {
    & $launcher.Source -3 -c 'import sys; sys.exit(0)' 2>$null
    if ($LASTEXITCODE -eq 0) {
        & $launcher.Source -3 $serverScript --lan
        exit $LASTEXITCODE
    }
}

$python = Get-Command python.exe -ErrorAction SilentlyContinue
if ($python -and $python.Source -notlike '*\Microsoft\WindowsApps\python.exe') {
    & $python.Source $serverScript --lan
    exit $LASTEXITCODE
}

$runtimes = Get-AppxPackage -Name 'OpenAI.CodexPrimaryRuntime*' | Sort-Object Version -Descending
foreach ($runtime in $runtimes) {
    $bundledPython = Join-Path $runtime.InstallLocation 'dependencies\python\python.exe'
    if ([IO.File]::Exists($bundledPython)) {
        & $bundledPython $serverScript --lan
        exit $LASTEXITCODE
    }
}

Write-Error 'Počítač nenašiel Python 3 potrebný pre lokálny server.'
exit 1
