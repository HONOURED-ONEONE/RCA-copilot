using Xunit;
using Moq;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Configuration;
using ControlPlane.Services;
using ControlPlane.Models;
using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;

namespace ControlPlane.Tests;

public class RunFolderPollerTests
{
    private readonly Mock<ILogger<RunFolderPoller>> _loggerMock = new();
    private readonly Mock<IServiceProvider> _serviceProviderMock = new();
    private readonly Mock<IMemoryStore> _memoryStoreMock = new();
    private readonly Mock<ILedgerService> _ledgerServiceMock = new();
    private readonly Mock<IPythonAnalyticsClient> _pythonClientMock = new();
    private readonly IConfiguration _configuration;

    private readonly string _testSharedPath = "test_shared_poller/current";

    public RunFolderPollerTests()
    {
        var myConfiguration = new Dictionary<string, string>
        {
            {"ControlPlane:SharedFolderCurrentPath", _testSharedPath},
            {"ControlPlane:PollingIntervalSeconds", "1"}
        };

        _configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(myConfiguration!)
            .Build();

        var scopeMock = new Mock<IServiceScope>();
        scopeMock.Setup(s => s.ServiceProvider.GetService(typeof(IPythonAnalyticsClient))).Returns(_pythonClientMock.Object);
        
        var scopeFactoryMock = new Mock<IServiceScopeFactory>();
        scopeFactoryMock.Setup(s => s.CreateScope()).Returns(scopeMock.Object);

        _serviceProviderMock.Setup(s => s.GetService(typeof(IServiceScopeFactory))).Returns(scopeFactoryMock.Object);
    }

    [Fact]
    public async Task PollFolderAsync_ProcessesNewRunSuccessfully()
    {
        // Arrange
        if (Directory.Exists(_testSharedPath)) Directory.Delete(_testSharedPath, true);
        Directory.CreateDirectory(_testSharedPath);
        
        File.WriteAllText(Path.Combine(_testSharedPath, "READY"), "");
        File.WriteAllText(Path.Combine(_testSharedPath, "manifest.json"), "{\"run_id\": \"run-123\"}");
        File.WriteAllText(Path.Combine(_testSharedPath, "logs.jsonl"), "{\"msg\": \"hello\"}\n");

        _pythonClientMock.Setup(c => c.AnalyzeRunAsync(It.IsAny<RunData>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new RCABundle { 
                Kept = "baseline", 
                Final = new PipelineResult { 
                    RunId = "run-123", 
                    Tss = 0.95,
                    EpistemicState = new EpistemicState() 
                } 
            });

        var poller = new RunFolderPoller(_loggerMock.Object, _serviceProviderMock.Object, _memoryStoreMock.Object, _ledgerServiceMock.Object, _configuration);

        // Act
        await poller.PollFolderAsync(CancellationToken.None);

        // Assert
        _pythonClientMock.Verify(c => c.AnalyzeRunAsync(It.Is<RunData>(r => r.Manifest.RunId == "run-123"), It.IsAny<CancellationToken>()), Times.Once);
        _memoryStoreMock.VerifySet(m => m.LatestAnalysis = It.IsAny<RCABundle>(), Times.Once);
        _ledgerServiceMock.Verify(l => l.RecordEventAsync("run-123", "AnalysisComplete", It.IsAny<string>()), Times.Once);

        // Cleanup
        if (Directory.Exists(_testSharedPath)) Directory.Delete(_testSharedPath, true);
    }
}
