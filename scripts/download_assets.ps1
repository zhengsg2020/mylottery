Param(
  [string]$AssetsDir = "$PSScriptRoot\..\assets\img",
  [string]$StaticDir = "$PSScriptRoot\..\static\img"
)

$ErrorActionPreference = "Stop"

function Ensure-Dir([string]$Path) {
  if (!(Test-Path $Path)) { New-Item -ItemType Directory -Path $Path | Out-Null }
}

function Download-File([string]$Url, [string]$OutFile) {
  Write-Host "Downloading $Url -> $OutFile"
  Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
}

Ensure-Dir $AssetsDir
Ensure-Dir $StaticDir

# Twemoji (CC-BY 4.0): https://github.com/twitter/twemoji
# We download a small set of PNGs used by both desktop and web UI.
$files = @(
  @{ name="slot.png";  url="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f3b0.png" },  # 🎰
  @{ name="ticket.png";url="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f3ab.png" },  # 🎫
  @{ name="globe.png"; url="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f310.png" },  # 🌐
  @{ name="money.png"; url="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f4b0.png" }   # 💰
)

foreach ($f in $files) {
  $a = Join-Path $AssetsDir $f.name
  $s = Join-Path $StaticDir $f.name
  if (!(Test-Path $a)) { Download-File $f.url $a } else { Write-Host "Exists: $a" }
  if (!(Test-Path $s)) { Copy-Item $a $s -Force } else { Write-Host "Exists: $s" }
}

@"
Assets downloaded.
- Desktop assets: $AssetsDir
- Web static:      $StaticDir

Attribution:
- Twemoji by Twitter, licensed CC-BY 4.0
  https://github.com/twitter/twemoji
"@ | Write-Host
