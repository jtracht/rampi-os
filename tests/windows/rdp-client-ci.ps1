# Microsoft ActiveX client, inside the disposable Windows fixture only.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted' -or
    $env:GITHUB_REPOSITORY -ne 'jtracht/rampi-os' -or $env:ImageOS -notlike 'win*') {
    throw 'Disposable GitHub Windows runner required.'
}
if ([Threading.Thread]::CurrentThread.ApartmentState -ne 'STA') { throw 'STA required.' }
Add-Type -ReferencedAssemblies System.Windows.Forms, System.Drawing, Microsoft.CSharp -TypeDefinition @'
using System;
using System.Diagnostics;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;
public sealed class RampiRdpControl : AxHost {
    public RampiRdpControl() : base(Type.GetTypeFromProgID("MsRdpClient9NotSafeForScripting", true).GUID.ToString()) {}
    public object Client { get { return GetOcx(); } }
}
public static class RampiRdpClientProbe {
    public static string Run(string server, string user, string password) {
        bool loggedIn = false, disconnected = false;
        int reason = 0;
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
            dynamic client = control.Client;
            client.Server = server;
            client.UserName = user;
            client.Domain = Environment.MachineName;
            client.AdvancedSettings9.EnableCredSspSupport = true;
            // 1 requires successful server authentication; never ignore certificates.
            client.AdvancedSettings9.AuthenticationLevel = 1u;
            client.AdvancedSettings9.ClearTextPassword = password;
            client.AdvancedSettings9.PromptForCredentials = false;
            Action login = () => { loggedIn = true; };
            Action<int> disconnect = value => { reason = value; disconnected = true; };
            ComEventsHelper.Combine((object)client, events, 3, login);
            ComEventsHelper.Combine((object)client, events, 4, disconnect);
            try {
                client.Connect();
                var timer = Stopwatch.StartNew();
                while (!loggedIn && !disconnected && timer.Elapsed.TotalSeconds < 60) {
                    Application.DoEvents();
                    Thread.Sleep(20);
                }
                if (!loggedIn && !disconnected) throw new TimeoutException("Actual RDP authentication timed out; no acceptance.");
                return loggedIn ? "login-complete" : "disconnected:" + reason;
            } finally {
                if (client.Connected != 0) client.Disconnect();
                ComEventsHelper.Remove((object)client, events, 3, login);
                ComEventsHelper.Remove((object)client, events, 4, disconnect);
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
