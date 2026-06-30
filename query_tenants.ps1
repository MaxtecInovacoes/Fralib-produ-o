Add-Type -AssemblyName System.Data

$conn = New-Object System.Data.Odbc.OdbcConnection
$conn.ConnectionString = "Driver={PostgreSQL ANSI};Server=localhost;Port=5432;Database=fralib_db;Uid=postgres;Pwd=fralib2024;"

try {
    $conn.Open()
    Write-Host "Connected via ODBC!"

    $cmd = $conn.CreateCommand()
    $cmd.CommandText = "SELECT id, email, plano, nicho FROM users ORDER BY id"

    $reader = $cmd.ExecuteReader()
    $users = @()
    while ($reader.Read()) {
        $users += @{
            id = $reader[0]
            email = $reader[1]
            plano = $reader[2]
            nicho = $reader[3]
        }
        Write-Host ("ID: {0}, Email: {1}, Plano: {2}, Nicho: {3}" -f $reader[0], $reader[1], $reader[2], $reader[3])
    }
    $reader.Close()

    # Get configs for each user
    foreach ($user in $users) {
        $uid = $user.id
        Write-Host ""
        Write-Host ("=" * 80)
        Write-Host ("TENANT: {0}" -f $user.email)
        Write-Host ("  ID: {0} | Plano: {1} | Nicho: {2}" -f $user.id, $user.plano, $user.nicho)
        Write-Host ""

        # SDR settings
        $cmd.CommandText = "SELECT config_value FROM user_configs WHERE user_id = $uid AND config_key = 'sdr_settings_v1'"
        $sdrReader = $cmd.ExecuteReader()
        if ($sdrReader.Read()) {
            $sdr = $sdrReader[0]
            Write-Host "  SDR_SETTINGS_V1:"
            $sdrObj = $sdr | ConvertFrom-Json
            Write-Host ("    agent_name: {0}" -f $sdrObj.agent_name)
            Write-Host ("    limits: {0}" -f ($sdrObj.limits | ConvertTo-Json -Compress))
            Write-Host ("    schedule: {0}" -f ($sdrObj.outbound_schedule | ConvertTo-Json -Compress))
            Write-Host ("    blocked_actions: {0}" -f ($sdrObj.blocked_actions | ConvertTo-Json -Compress))
            Write-Host ("    allowed_actions: {0}" -f ($sdrObj.allowed_actions | ConvertTo-Json -Compress))
            Write-Host ("    handoff: {0}" -f ($sdrObj.handoff | ConvertTo-Json -Compress))
        } else {
            Write-Host "  SDR_SETTINGS_V1: NOT CONFIGURED"
        }
        $sdrReader.Close()
        Write-Host ""

        # Pipeline state
        $cmd.CommandText = "SELECT config_value FROM user_configs WHERE user_id = $uid AND config_key = 'pipeline_state'"
        $pipeReader = $cmd.ExecuteReader()
        if ($pipeReader.Read()) {
            Write-Host "  PIPELINE_STATE:"
            $pipe = $pipeReader[0] | ConvertFrom-Json
            $pipe | ConvertTo-Json -Depth 5 | ForEach-Object { Write-Host "    $_" }
        } else {
            Write-Host "  PIPELINE_STATE: NOT CONFIGURED"
        }
        $pipeReader.Close()
        Write-Host ""

        # Lead supply config
        $cmd.CommandText = "SELECT config_value FROM user_configs WHERE user_id = $uid AND config_key = 'lead_supply_config'"
        $lscReader = $cmd.ExecuteReader()
        if ($lscReader.Read()) {
            Write-Host "  LEAD_SUPPLY_CONFIG:"
            $lsc = $lscReader[0] | ConvertFrom-Json
            $lsc | ConvertTo-Json -Depth 5 | ForEach-Object { Write-Host "    $_" }
        } else {
            Write-Host "  LEAD_SUPPLY_CONFIG: NOT CONFIGURED"
        }
        $lscReader.Close()
        Write-Host ""

        # Lead counts
        $cmd.CommandText = "SELECT status, COUNT(*) as count FROM leads WHERE user_id = $uid GROUP BY status"
        $leadReader = $cmd.ExecuteReader()
        Write-Host "  LEAD STATUS COUNTS:"
        $pendingSdr = 0
        $pendingWpp = 0
        while ($leadReader.Read()) {
            Write-Host ("    {0}: {1}" -f $leadReader[0], $leadReader[1])
            if ($leadReader[0] -eq 'pending_sdr_send') { $pendingSdr = $leadReader[1] }
            if ($leadReader[0] -eq 'pendente_wpp') { $pendingWpp = $leadReader[1] }
        }
        Write-Host ("  -> Leads stuck at pending_sdr_send: {0}" -f $pendingSdr)
        Write-Host ("  -> Leads stuck at pendente_wpp: {0}" -f $pendingWpp)
        $leadReader.Close()
        Write-Host ""
    }

    $conn.Close()
} catch {
    Write-Host ("Error: {0}" -f $_.Exception.Message)
}
