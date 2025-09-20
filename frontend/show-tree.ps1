param (
    [string]$Path = ".",
    [string]$OutFile = "project-tree.txt",
    [int]$MaxDepth = 3
)

function Show-Tree {
    param (
        [string]$Path,
        [string]$Indent = "",
        [int]$Depth = 0,
        [int]$MaxDepth = 3
    )

    if ($Depth -ge $MaxDepth) {
        return
    }

    Get-ChildItem -Path $Path | Where-Object {
        -not ($_.Name -in @("node_modules", ".git", ".next", "dist"))
    } | Sort-Object PSIsContainer, Name | ForEach-Object {
        if ($_.PSIsContainer) {
            "$Indent+-- $($_.Name)" | Out-File -FilePath $OutFile -Append
            Show-Tree -Path $_.FullName -Indent ("$Indent|   ") -Depth ($Depth + 1) -MaxDepth $MaxDepth
        } else {
            "$Indent+-- $($_.Name)" | Out-File -FilePath $OutFile -Append
        }
    }
}

# Clear file
"" | Out-File $OutFile

Write-Host "Generating clean project tree from $Path ..."
"Project structure:`n" | Out-File $OutFile -Append
Show-Tree -Path $Path -MaxDepth $MaxDepth
Write-Host "✅ Project tree saved to $OutFile"
