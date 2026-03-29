using System.Text.Json;
using ControlPlane.Models;

namespace ControlPlane.Services;

public interface ILedgerService
{
    Task RecordClaimsAsync(string runId, List<HealthClaim> claims);
    Task RecordContradictionsAsync(string runId, List<Contradiction> contradictions);
    Task RecordEventAsync(string runId, string eventType, string details);
    
    Task<List<ClaimRecord>> GetClaimsAsync();
    Task<List<ContradictionRecord>> GetContradictionsAsync();
    Task<List<LedgerEntry>> GetLedgerEntriesAsync();
}

public class LedgerService : ILedgerService
{
    private readonly string _storagePath = "ledger_data.json";
    private readonly ILogger<LedgerService> _logger;
    private static readonly SemaphoreSlim _lock = new(1, 1);

    public LedgerService(ILogger<LedgerService> logger)
    {
        _logger = logger;
    }

    public async Task RecordClaimsAsync(string runId, List<HealthClaim> claims)
    {
        var records = claims.Select(c => new ClaimRecord 
        { 
            RunId = runId, 
            Service = c.Service, 
            State = c.Type, 
            Confidence = c.Confidence 
        }).ToList();
        
        await AppendToStoreAsync("claims", records);
    }

    public async Task RecordContradictionsAsync(string runId, List<Contradiction> contradictions)
    {
        var records = contradictions.Select(c => new ContradictionRecord 
        { 
            RunId = runId, 
            Service = c.Service, 
            Description = c.Description, 
            Severity = c.Severity 
        }).ToList();
        
        await AppendToStoreAsync("contradictions", records);
    }

    public async Task RecordEventAsync(string runId, string eventType, string details)
    {
        var entry = new LedgerEntry { RunId = runId, EventType = eventType, Details = details };
        await AppendToStoreAsync("events", new List<LedgerEntry> { entry });
    }

    public async Task<List<ClaimRecord>> GetClaimsAsync() => await ReadFromStoreAsync<ClaimRecord>("claims");
    public async Task<List<ContradictionRecord>> GetContradictionsAsync() => await ReadFromStoreAsync<ContradictionRecord>("contradictions");
    public async Task<List<LedgerEntry>> GetLedgerEntriesAsync() => await ReadFromStoreAsync<LedgerEntry>("events");

    private async Task AppendToStoreAsync<T>(string key, List<T> newItems)
    {
        await _lock.WaitAsync();
        try
        {
            var store = await FullLoadAsync();
            if (!store.ContainsKey(key)) store[key] = new List<object>();
            foreach (var item in newItems) store[key].Add(item!);
            await File.WriteAllTextAsync(_storagePath, JsonSerializer.Serialize(store));
        }
        finally
        {
            _lock.Release();
        }
    }

    private async Task<List<T>> ReadFromStoreAsync<T>(string key)
    {
        await _lock.WaitAsync();
        try
        {
            var store = await FullLoadAsync();
            if (!store.ContainsKey(key)) return new List<T>();
            return JsonSerializer.Deserialize<List<T>>(JsonSerializer.Serialize(store[key])) ?? new List<T>();
        }
        finally
        {
            _lock.Release();
        }
    }

    private async Task<Dictionary<string, List<object>>> FullLoadAsync()
    {
        if (!File.Exists(_storagePath)) return new Dictionary<string, List<object>>();
        var json = await File.ReadAllTextAsync(_storagePath);
        return JsonSerializer.Deserialize<Dictionary<string, List<object>>>(json) ?? new Dictionary<string, List<object>>();
    }
}
