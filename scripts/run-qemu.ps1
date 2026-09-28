# ============================================================
# XII OS — QEMU Boot Test Runner (Windows PowerShell)
# scripts/run-qemu.ps1
# ============================================================
# Launches XII OS in QEMU from a Windows host for boot testing.
#
# Requirements:
#   - QEMU for Windows installed:
#     https://www.qemu.org/download/#windows
#     (Default path: C:\Program Files\qemu\)
#   - An ISO at build\xii-os-1.0-genesis-amd64.iso
#
# Usage:
#   .\run-qemu.ps1
#   .\run-qemu.ps1 -IsoPath ".\build\xii-os-1.0-genesis-amd64.iso"
#   .\run-qemu.ps1 -BootMode bios -RamMB 1024
#   .\run-qemu.ps1 -Headless
# ============================================================

[CmdletBinding()]
param(
    [string]$IsoPath   = "",
    [string]$BootMode  = "bios",   # "bios" or "uefi" (UEFI requires OVMF)
    [int]   $RamMB     = 2048,
    [int]   $Cpus      = 2,
    [switch]$Headless,
    [string]$QemuPath  = "C:\Program Files\qemu"
)

# ────────────────────────────────────────────────────────────
# Color helpers
# ────────────────────────────────────────────────────────────
function Write-Header($msg) { Write-Host "`n[XII QEMU] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)     { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warn($msg)   { Write-Host "  ⚠ $msg" -ForegroundColor Yellow }
function Write-Err($msg)    { Write-Host "  ✗ ERROR: $msg" -ForegroundColor Red }
function Write-Sep()        { Write-Host ("─" * 50) -ForegroundColor DarkCyan }

# ────────────────────────────────────────────────────────────
# Resolve paths
# ────────────────────────────────────────────────────────────
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

if ([string]::IsNullOrEmpty($IsoPath)) {
    $IsoPath = Join-Path $ProjectRoot "build\xii-os-1.0-genesis-amd64.iso"
}

$QemuExe = Join-Path $QemuPath "qemu-system-x86_64.exe"

# OVMF firmware paths (for UEFI mode)
$OvmfCode = Join-Path $QemuPath "share\edk2-x86_64-code.fd"
$OvmfVarsSrc = Join-Path $QemuPath "share\edk2-i386-vars.fd"
$OvmfVarsCopy = Join-Path $ScriptDir "ovmf-vars-copy.fd"

Write-Sep
Write-Header "XII OS QEMU Boot Test (Windows)"
Write-Host "  ISO         : $IsoPath"
Write-Host "  Boot Mode   : $BootMode"
Write-Host "  RAM         : $RamMB MB  |  CPUs: $Cpus"
Write-Host "  QEMU Path   : $QemuPath"
Write-Sep

# ────────────────────────────────────────────────────────────
# Preflight checks
# ────────────────────────────────────────────────────────────
Write-Header "Preflight Checks..."

if (-not (Test-Path $QemuExe)) {
    Write-Err "QEMU not found at: $QemuExe"
    Write-Host ""
    Write-Host "  Download QEMU for Windows from:" -ForegroundColor Yellow
    Write-Host "  https://www.qemu.org/download/#windows" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Or install via winget:" -ForegroundColor Yellow
    Write-Host "  winget install SoftwareFreedomConservancy.QEMU" -ForegroundColor Yellow
    exit 1
}
Write-Ok "QEMU found: $QemuExe"

if (-not (Test-Path $IsoPath)) {
    Write-Err "ISO not found at: $IsoPath"
    Write-Host "  Run bootstrap-base.sh and build-iso.sh in WSL first." -ForegroundColor Yellow
    exit 1
}
Write-Ok "ISO found: $IsoPath"

# ────────────────────────────────────────────────────────────
# Build QEMU arguments
# ────────────────────────────────────────────────────────────
$QemuArgs = @(
    "-name", "XII OS - Phase 1 Boot Test",
    "-machine", "type=q35",
    "-cpu", "qemu64",
    "-smp", "$Cpus",
    "-m", "${RamMB}M",
    "-cdrom", "`"$IsoPath`"",
    "-boot", "d",
    "-device", "virtio-net-pci,netdev=net0",
    "-netdev", "user,id=net0",
    "-audiodev", "none,id=noaudio",
    "-serial", "stdio"
)

# UEFI boot mode
if ($BootMode -eq "uefi") {
    if (Test-Path $OvmfCode) {
        # Copy OVMF vars to a writable location (UEFI needs a writable NVRAM)
        if (-not (Test-Path $OvmfVarsCopy)) {
            Copy-Item $OvmfVarsSrc $OvmfVarsCopy
        }
        $QemuArgs += @(
            "-drive", "if=pflash,format=raw,readonly=on,file=`"$OvmfCode`"",
            "-drive", "if=pflash,format=raw,file=`"$OvmfVarsCopy`""
        )
        Write-Ok "UEFI mode: OVMF firmware found."
    } else {
        Write-Warn "OVMF not found — falling back to BIOS mode."
        $BootMode = "bios"
    }
}

# Display
if ($Headless) {
    $QemuArgs += @("-display", "none", "-vga", "none")
    Write-Warn "Headless mode: output via serial console in this window."
} else {
    $QemuArgs += @("-display", "gtk", "-vga", "virtio")
}

# ────────────────────────────────────────────────────────────
# Launch QEMU
# ────────────────────────────────────────────────────────────
Write-Sep
Write-Header "Launching QEMU..."
Write-Host "  Boot mode: $BootMode" -ForegroundColor White
Write-Host "  Close the QEMU window to stop. Press Ctrl+C here for headless." -ForegroundColor DarkGray
Write-Sep

$ArgString = $QemuArgs -join " "
Write-Host "  CMD: qemu-system-x86_64 $ArgString`n" -ForegroundColor DarkGray

try {
    Start-Process -FilePath $QemuExe -ArgumentList $QemuArgs -NoNewWindow -Wait
    Write-Ok "QEMU session ended normally."
}
catch {
    Write-Err "QEMU failed to launch: $_"
    exit 1
}
