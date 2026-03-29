using System.Text.Json;
using ControlPlane.Models;

namespace ControlPlane.Services;

public class RunFolderPoller : BackgroundService
{
    private readonly ILogger<RunFolderPoller> _logger;
    private readonly IServiceProvider _serviceProvider;
    private readonly IMemoryStore _memoryStore;
    private readonly ILedgerService _ledgerService;
    private readonly string _sharedFolderPath;
    private readonly TimeSpan _pollingInterval;

    private string _lastProcessedRunId = string.Empty;

    public RunFolderPoller(
        ILogger<RunFolderPoller> logger, 
        IServiceProvider serviceProvider,
        IMemoryStore memoryStore,
        ILedgerService ledgerService,
        IConfiguration configuration)
    {
        _logger = logger;
        _serviceProvider = serviceProvider;
        _memoryStore = memoryStore;
        _ledgerService = ledgerService;
        
        _sharedFolderPath = configuration.GetValue<string>("ControlPlane:SharedFolderCurrentPath") ?? "shared_demo_root/current";
        var intervalSecs = configuration.GetValue<int>("ControlPlane:PollingIntervalSeconds");
        _pollingInterval = TimeSpan.FromSeconds(intervalSecs > 0 ? intervalSecs : 2);
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("RunFolderPoller started. Watching {FolderPath}", _sharedFolderPath);
        _memoryStore.ControlPlaneStatus = "Running";

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await PollFolderAsync(stoppingToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error occurred during run folder polling.");
            }

            await Task.Delay(_pollingInterval, stoppingToken);
        }
    }

    internal async Task PollFolderAsync(CancellationToken stoppingToken)
    {
        if (!Directory.Exists(_sharedFolderPath))
        {
            _logger.LogWarning("Shared folder does not exist: {Path}", _sharedFolderPath);
            return;
        }

        var readyPath = Path.Combine(_sharedFolderPath, "READY");
        var manifestPath = Path.Combine(_sharedFolderPath, "manifest.json");

        if (!File.Exists(readyPath) || !File.Exists(manifestPath)) return;

        var manifestJson = await File.ReadAllTextAsync(manifestPath, stoppingToken);
        var manifest = JsonSerializer.Deserialize<Manifest>(manifestJson);
        var runId = manifest?.RunId;

        if (manifest == null || string.IsNullOrEmpty(runId))
        {
            _logger.LogWarning("Manifest is null or missing run_id in {Path}", manifestPath);
            return;
        }

        if (runId != _lastProcessedRunId)
        {
            _logger.LogInformation("Detected new run: {RunId}. Processing...", runId);
            _memoryStore.ControlPlaneStatus = $"Processing {runId}";

            var runData = new RunData { Manifest = manifest! };
            
            runData.Alerts = await LoadJsonlAsync(Path.Combine(_sharedFolderPath, "alerts.jsonl"), stoppingToken);
            runData.Logs = await LoadJsonlAsync(Path.Combine(_sharedFolderPath, "logs.jsonl"), stoppingToken);
            runData.Metrics = await LoadJsonlAsync(Path.Combine(_sharedFolderPath, "metrics.jsonl"), stoppingToken);
            runData.Traces = await LoadJsonlAsync(Path.Combine(_sharedFolderPath, "traces.jsonl"), stoppingToken);
            runData.Changes = await LoadJsonlAsync(Path.Combine(_sharedFolderPath, "changes.jsonl"), stoppingToken);

            _memoryStore.LatestRunData = runData;

            using var scope = _serviceProvider.CreateScope();
            var pythonClient = scope.ServiceProvider.GetRequiredService<IPythonAnalyticsClient>();
            
            var analysisResult = await pythonClient.AnalyzeRunAsync(runData, stoppingToken);
            if (analysisResult != null)
            {
                _memoryStore.LatestAnalysis = analysisResult;
                _logger.LogInformation("Successfully processed run {RunId} via Python Engine.", runId);

                var finalResult = analysisResult.Final;
                if (finalResult?.EpistemicState != null)
                {
                    await _ledgerService.RecordClaimsAsync(runId, finalResult.EpistemicState.HealthClaims);
                    await _ledgerService.RecordContradictionsAsync(runId, finalResult.EpistemicState.Contradictions);
                }
                await _ledgerService.RecordEventAsync(runId, "AnalysisComplete", $"Kept: {analysisResult.Kept}");

                if (finalResult?.EpistemicState != null)
                {
                    var claims = finalResult.EpistemicState.HealthClaims;
                    var contradictions = finalResult.EpistemicState.Contradictions;

                    _logger.LogInformation("CEF: Processed {ClaimCount} health claims and {ContradictionCount} contradictions.", 
                        claims.Count, contradictions.Count);

                    foreach (var ct in contradictions)
                    {
                        _logger.LogWarning("CEF Contradiction [{Severity}] in {Scope}: {Desc}", 
                            ct.Severity, ct.Service, ct.Description);
                        
                        if (ct.Severity == "HIGH")
                        {
                            _logger.LogCritical("CEF: High severity contradiction detected. Triggering automated probe orchestration...");
                        }
                    }
                }

                if (analysisResult.Probes != null && analysisResult.Probes.Count > 0)
                {
                    _logger.LogInformation("CEF: {ProbeCount} probes recommended by analytical engine.", analysisResult.Probes.Count);
                }

                _memoryStore.ControlPlaneStatus = $"Idle - Last processed {runId}";
                _lastProcessedRunId = runId; // Only mark as processed if we actually got a result.
            }
            else
            {
                _logger.LogWarning("Analysis returned null for {RunId}. Will retry on next poll.", runId);
                _memoryStore.ControlPlaneStatus = $"Failed processing {runId} - will retry";
            }
        }
    }

    private async Task<List<object>> LoadJsonlAsync(string filePath, CancellationToken cancellationToken)
    {
        var items = new List<object>();
        if (!File.Exists(filePath)) return items;

        try
        {
            var lines = await File.ReadAllLinesAsync(filePath, cancellationToken);
            foreach (var line in lines)
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                try
                {
                    var obj = JsonSerializer.Deserialize<object>(line);
                    if (obj != null) items.Add(obj);
                }
                catch (JsonException ex)
                {
                    _logger.LogWarning(ex, "Failed to deserialize line in {Path}", filePath);
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to read JSONL file {Path}", filePath);
        }
        return items;
    }
}
