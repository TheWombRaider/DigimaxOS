<#
.SYNOPSIS
  Read-only collection of Samsung Digimax USB/disk facts for a DigimaxOS compatibility report.

.DESCRIPTION
  Queries Plug and Play and storage metadata only. It does NOT read or copy any photos,
  does NOT open the raw disk, does NOT mount, format or write anything.
  Output is JSON suitable for `digimax discover --import FILE`.
  Windows-generated instance IDs are reduced to their VID/PID part; review the file before
  sharing it publicly.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File Get-DigimaxInfo.ps1 > digimax-report.json
#>
[CmdletBinding()]
param(
  [string[]] $VendorIds = @('0839', '04FC')
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Get-Prop($id, $key) {
  (Get-PnpDeviceProperty -InstanceId $id -KeyName $key -ErrorAction SilentlyContinue).Data
}

$pattern = ($VendorIds | ForEach-Object { "USB\\VID_$_&PID_" }) -join '|'
$devices = @()
foreach ($dev in Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match "^($pattern)" -and $_.InstanceId -notmatch '&MI_' }) {
  if ($dev.InstanceId -notmatch 'VID_([0-9A-F]{4})&PID_([0-9A-F]{4})') { continue }
  $vid = $Matches[1]; $productId = $Matches[2]
  $hw = @(Get-Prop $dev.InstanceId 'DEVPKEY_Device_HardwareIds')
  $rev = $null
  foreach ($h in $hw) { if ($h -match 'REV_([0-9A-F]{4})') { $rev = $Matches[1] } }
  $ifaces = @()
  foreach ($c in @(Get-Prop $dev.InstanceId 'DEVPKEY_Device_CompatibleIds')) {
    if ($c -match '^USB\\Class_([0-9A-F]{2})&SubClass_([0-9A-F]{2})&Prot_([0-9A-F]{2})$') {
      $ifaces += [ordered]@{ class = [Convert]::ToInt32($Matches[1], 16); subclass = [Convert]::ToInt32($Matches[2], 16); protocol = [Convert]::ToInt32($Matches[3], 16) }
    }
  }
  $disks = @()
  foreach ($d in Get-Disk | Where-Object { $_.BusType -eq 'USB' -and $_.FriendlyName -match 'SAMSUNG|DIGITAL CAMERA' }) {
    $parts = @(Get-Partition -DiskNumber $d.Number -ErrorAction SilentlyContinue | ForEach-Object {
      $vol = $null
      if ($_.DriveLetter) { $vol = Get-Volume -DriveLetter $_.DriveLetter -ErrorAction SilentlyContinue }
      [ordered]@{ offset = $_.Offset; size = $_.Size; mbr_type = $_.MbrType;
                  filesystem = $vol.FileSystem; cluster_bytes = $vol.AllocationUnitSize;
                  volume_size = $vol.Size; volume_free = $vol.SizeRemaining }
    })
    $disks += [ordered]@{ number = $d.Number; friendly_name = $d.FriendlyName; size = $d.Size;
                          logical_sector = $d.LogicalSectorSize; partition_style = "$($d.PartitionStyle)";
                          firmware_version = $d.FirmwareVersion; partitions = $parts }
  }
  $devices += [ordered]@{
    vendor_id = $vid; product_id = $productId; bcd_device = $rev
    status = "$($dev.Status)"; service = (Get-Prop $dev.InstanceId 'DEVPKEY_Device_Service')
    bus_reported_description = ("$(Get-Prop $dev.InstanceId 'DEVPKEY_Device_BusReportedDeviceDesc')").Trim()
    interfaces = $ifaces; disks = $disks
  }
}

[ordered]@{
  tool = 'Get-DigimaxInfo.ps1'; schema = 1
  collected_utc = (Get-Date).ToUniversalTime().ToString('o')
  host_os = [System.Environment]::OSVersion.VersionString
  devices = $devices
} | ConvertTo-Json -Depth 8
