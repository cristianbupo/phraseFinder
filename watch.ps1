# Live view of the Spanish subtitle downloads. Ctrl+C closes the view; the download keeps going.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$transcripts = Join-Path $PSScriptRoot "transcripts"
$today = (Get-Date).Date
while ($true) {
    $log = Get-ChildItem "$env:TEMP\cs_*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
    $running = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*channelSearcher*' }).Count -gt 0
    $lines = @()
    if ($log) {
        # The download is still writing this file, so open it without locking
        $stream = [System.IO.File]::Open($log.FullName, 'Open', 'Read', 'ReadWrite')
        $reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::UTF8)
        $text = $reader.ReadToEnd()
        $reader.Close()
        $lines = @($text -split "[`r`n]+" | Where-Object { $_.Trim() })
    }
    Clear-Host
    "Spanish subtitle downloads   " + (Get-Date -Format "HH:mm:ss")
    ""
    if ($running -and $log) {
        "Now downloading: " + ($log.BaseName -replace '^cs_', '')
        $last = if ($lines.Count) { $lines[-1] } else { "" }
        if ($last -match '(\d+)/(\d+).*Saved: (\d+).*Skipped: (\d+).*Failed: (\d+)') {
            $filled = [int](40 * [int]$Matches[1] / [int]$Matches[2])
            "[" + ("#" * $filled) + ("." * (40 - $filled)) + "]  checked " + $Matches[1] + " of " + $Matches[2]
            "Saved: " + $Matches[3] + "   Skipped: " + $Matches[4] + "   Failed: " + $Matches[5]
        } elseif ($last -match 'Fetching videos\.\.\. (\d+) found') {
            "Listing the channel's videos: " + $Matches[1] + " found so far"
        } else {
            "Starting..."
        }
    } elseif ($log) {
        "Nothing is downloading right now. Last channel: " + ($log.BaseName -replace '^cs_', '')
        $lines | Select-Object -Last 6
    } else {
        "No download has run yet."
    }
    ""
    "Saved on this computer, per channel:"
    Get-ChildItem $transcripts -Directory | Where-Object { Test-Path (Join-Path $_.FullName "video_list.txt") } | ForEach-Object {
        $count = @(Get-ChildItem $_.FullName -Filter *.json).Count
        "  {0,5}  {1}" -f $count, ($_.Name -replace '_', ' ')
    }
    ""
    "Ctrl+C closes this view. The download keeps going."
    Start-Sleep 5
}
