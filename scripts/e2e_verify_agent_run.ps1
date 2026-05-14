# Requires: docker compose up (api, worker, redis, postgres), current repo images.
# Uses registered filesystem v2 agent: Competitor Intelligence Agent
# (market_research.research_agent is NOT registered by agent_runtime.loader — see docs/E2E_AGENT_VERIFICATION.md)

$ErrorActionPreference = "Stop"
$base = if ($env:API_BASE) { $env:API_BASE } else { "http://127.0.0.1:8000" }
$headers = @{
    "Content-Type" = "application/json"
    "X-Project-ID" = "00000000-0000-4000-8000-000000000002"
}
$body = @{
    agent_name = "Competitor Intelligence Agent"
    task_text  = "E2E script"
    input      = @{ urls = @("https://example.com") }
} | ConvertTo-Json -Depth 6

Write-Host "POST $base/agents/v2/run"
$r = Invoke-RestMethod -Uri "$base/agents/v2/run" -Method POST -Headers $headers -Body $body
Write-Host "Response:" ($r | ConvertTo-Json -Compress)
$tid = $r.task_id
Write-Host "`nWorker logs (last 40 lines):"
docker logs agent-cloud-worker-1 2>&1 | Select-Object -Last 40
Write-Host "`nDB status for task $tid :"
docker exec agent-cloud-postgres-1 psql -U agent -d agent_cloud -t -c "SELECT id, status FROM tasks WHERE id = '$tid';"
