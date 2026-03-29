using Xunit;
using Moq;
using Microsoft.Extensions.Logging;
using ControlPlane.Services;
using ControlPlane.Models;
using System.IO;

namespace ControlPlane.Tests;

public class LedgerServiceTests
{
    private readonly Mock<ILogger<LedgerService>> _loggerMock = new();

    [Fact]
    public async Task RecordEventAsync_AppendsToFile()
    {
        var storagePath = "ledger_data.json";
        if (File.Exists(storagePath)) File.Delete(storagePath);

        var service = new LedgerService(_loggerMock.Object);

        await service.RecordEventAsync("run-1", "TestEvent", "Details");
        await service.RecordEventAsync("run-1", "TestEvent2", "Details2");

        Assert.True(File.Exists(storagePath));
        var entries = await service.GetLedgerEntriesAsync();
        Assert.Equal(2, entries.Count);
        Assert.Contains(entries, e => e.EventType == "TestEvent");
        Assert.Contains(entries, e => e.EventType == "TestEvent2");

        if (File.Exists(storagePath)) File.Delete(storagePath);
    }

    [Fact]
    public async Task RecordClaimsAsync_StoresClaims()
    {
        var storagePath = "ledger_data.json";
        if (File.Exists(storagePath)) File.Delete(storagePath);

        var service = new LedgerService(_loggerMock.Object);
        var claims = new List<HealthClaim> { new HealthClaim { Service = "svc1", Type = "HEALTHY", Confidence = 0.9 } };

        await service.RecordClaimsAsync("run-2", claims);

        var stored = await service.GetClaimsAsync();
        Assert.Single(stored);
        Assert.Equal("svc1", stored[0].Service);

        if (File.Exists(storagePath)) File.Delete(storagePath);
    }
}
