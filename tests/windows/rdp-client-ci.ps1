# Microsoft ActiveX client, inside the disposable Windows fixture only.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted' -or
    $env:GITHUB_REPOSITORY -ne 'jtracht/rampi-os' -or $env:ImageOS -notlike 'win*') {
    throw 'Disposable GitHub Windows runner required.'
}
if ([Threading.Thread]::CurrentThread.ApartmentState -ne 'STA') { throw 'STA required.' }
# Reuse the installed Microsoft SDK to import the actual system type library.
# This avoids guessed COM dispatch members or a handwritten interface vtable.
$sdkRoot = Join-Path ${env:ProgramFiles(x86)} 'Microsoft SDKs/Windows'
$importers = @(Get-ChildItem -LiteralPath $sdkRoot -Filter TlbImp.exe -File -Recurse |
    Sort-Object @{Expression={ $_.FullName -match '\\x64\\' }; Descending=$true}, FullName)
if (-not $importers.Count) { throw 'Installed Microsoft SDK type-library importer missing.' }
$interopDirectory = Join-Path $env:RUNNER_TEMP ('rampi-rdp-interop-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $interopDirectory | Out-Null
$interopAssembly = Join-Path $interopDirectory 'MSTSCLib.dll'
& $importers[0].FullName "$env:WINDIR/System32/mstscax.dll" "/out:$interopAssembly" /namespace:MSTSCLib /machine:X64 /silent /nologo | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Actual Microsoft RDP type-library import failed.' }
[Reflection.Assembly]::LoadFrom($interopAssembly) | Out-Null
Add-Type -ReferencedAssemblies System.Windows.Forms, System.Drawing, System.Core, $interopAssembly -TypeDefinition @'
using System;
using System.Diagnostics;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;
public sealed class RampiRdpControl : AxHost {
    // Microsoft's documented CLSID; the class's display name is not a ProgID.
    public RampiRdpControl() : base("8B918B82-7985-4C24-89DF-C33AD2BBFBCD") {}
    public object Client { get { return GetOcx(); } }
}
public static class RampiRdpClientProbe {
    public static string Run(string server, string user, string password) {
        bool loggedIn = false, disconnected = false;
        int reason = 0;
        int? logonError = null;
        Guid events = new Guid("336d5562-efa8-482e-8cb3-c5c0fc7a7db6");
        using (var form = new Form())
        using (var control = new RampiRdpControl()) {
            form.ShowInTaskbar = false;
            form.StartPosition = FormStartPosition.Manual;
            form.Location = new System.Drawing.Point(-10000, -10000);
            form.Size = new System.Drawing.Size(800, 600);
            ((ISupportInitialize)control).BeginInit();
            control.Dock = DockStyle.Fill;
            form.Controls.Add(control);
            ((ISupportInitialize)control).EndInit();
            form.Show();
            Application.DoEvents();
            var client = (MSTSCLib.IMsRdpClient9)control.Client;
            client.Server = server;
            client.UserName = user;
            client.Domain = Environment.MachineName;
            client.AdvancedSettings9.EnableCredSspSupport = true;
            // 1 requires successful server authentication; never ignore certificates.
            client.AdvancedSettings9.AuthenticationLevel = 1u;
            client.AdvancedSettings9.ClearTextPassword = password;
            var credentials = (MSTSCLib.IMsRdpClientNonScriptable3)control.Client;
            credentials.PromptForCredentials = false;
            ((MSTSCLib.IMsRdpClientNonScriptable4)control.Client).PromptForCredsOnClient = false;
            Action login = () => { loggedIn = true; };
            Action<int> disconnect = value => { reason = value; disconnected = true; };
            Action<int> failedLogon = value => {
                // Documented credential failures, not Winlogon's continue/reconnect notices.
                if (value == 0 || value == 1 || value == 2 || value == -1 || value < -1000)
                    logonError = value;
            };
            var logonMethod = typeof(MSTSCLib.IMsTscAxEvents).GetMethod("OnLogonError");
            if (logonMethod == null) throw new InvalidOperationException("System RDP logon-error event missing.");
            var logonId = (DispIdAttribute)Attribute.GetCustomAttribute(logonMethod, typeof(DispIdAttribute));
            if (logonId == null) throw new InvalidOperationException("System RDP logon-error dispatch metadata missing.");
            ComEventsHelper.Combine((object)client, events, 3, login);
            ComEventsHelper.Combine((object)client, events, 4, disconnect);
            ComEventsHelper.Combine((object)client, events, logonId.Value, failedLogon);
            try {
                client.Connect();
                var timer = Stopwatch.StartNew();
                while (!loggedIn && !disconnected && !logonError.HasValue && timer.Elapsed.TotalSeconds < 60) {
                    Application.DoEvents();
                    Thread.Sleep(20);
                }
                if (!loggedIn && !disconnected && !logonError.HasValue) throw new TimeoutException("Actual RDP authentication timed out; no acceptance.");
                return loggedIn ? "login-complete" : logonError.HasValue
                    ? "credential-rejected:" + logonError.Value : "disconnected:" + reason;
            } finally {
                if (client.Connected != 0) client.Disconnect();
                ComEventsHelper.Remove((object)client, events, 3, login);
                ComEventsHelper.Remove((object)client, events, 4, disconnect);
                ComEventsHelper.Remove((object)client, events, logonId.Value, failedLogon);
                form.Close();
            }
        }
    }
}
'@
try {
    [RampiRdpClientProbe]::Run($env:COMPUTERNAME, $env:RAMPI_CI_RDP_USER, $env:RAMPI_CI_RDP_PASSWORD)
} finally {
    Remove-Item Env:RAMPI_CI_RDP_PASSWORD -ErrorAction SilentlyContinue
}
