using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;

string variant = args.Single();
string[] allowed = ["baseline", "di-transitive-unchecked", "factory-capture", "cancel-before", "cancel-after"];
if (!allowed.Contains(variant)) throw new ArgumentException("Unknown reviewed variant");
var checks = new List<object>();
bool failed = false;
void Check(string id, bool passed) {
    checks.Add(new {id, status = passed ? "PASSED" : "FAILED"});
    failed |= !passed;
}
bool captureRejected = false;
try {
    var services = new ServiceCollection();
    services.AddScoped<RequestScope>();
    services.AddTransient<Middle>();
    services.AddSingleton<Capture>();
    using var provider = services.BuildServiceProvider(new ServiceProviderOptions {
        ValidateScopes = variant != "di-transitive-unchecked", ValidateOnBuild = true});
    _ = provider.GetRequiredService<Capture>();
} catch (Exception error) when (error is AggregateException or InvalidOperationException) {
    string reason = error.GetBaseException().Message;
    captureRejected = reason.Contains(nameof(RequestScope)) && reason.Contains("singleton", StringComparison.OrdinalIgnoreCase);
}
Check("transitive_scoped_capture_rejected", captureRejected);

var factoryServices = new ServiceCollection();
factoryServices.AddScoped<RequestScope>();
using var root = factoryServices.BuildServiceProvider(new ServiceProviderOptions {ValidateScopes = true});
RequestScope? first, second;
bool scopesValid = true;
if (variant == "factory-capture") {
    using (var scope = root.CreateScope()) {first = scope.ServiceProvider.GetRequiredService<RequestScope>();}
    second = first;
    try { first.Touch(); } catch (ObjectDisposedException) {scopesValid = false;}
} else {
    using (var scope = root.CreateScope()) {first = scope.ServiceProvider.GetRequiredService<RequestScope>(); first.Touch();}
    using (var scope = root.CreateScope()) {second = scope.ServiceProvider.GetRequiredService<RequestScope>(); second.Touch();}
}
Check("factory_owns_distinct_disposed_scopes", scopesValid && first != second && first.Disposed && second.Disposed);

using var before = new CancellationTokenSource();
before.Cancel();
var earlyLedger = new Ledger();
bool earlyCancelled = false;
try { await earlyLedger.Commit(before, checkBefore: variant != "cancel-before", checkAfter: false); }
catch (OperationCanceledException error) {earlyCancelled = error.CancellationToken == before.Token;}
Check("cancellation_before_commit_has_no_effect", earlyCancelled && !earlyLedger.Committed);

using var after = new CancellationTokenSource();
var committedLedger = new Ledger();
bool acknowledged = false;
try { await committedLedger.Commit(after, checkBefore: true, checkAfter: variant == "cancel-after"); acknowledged = true; }
catch (OperationCanceledException) { }
Check("cancellation_after_commit_preserves_acknowledgment", acknowledged && committedLedger.Committed);
Console.WriteLine(JsonSerializer.Serialize(new {stack = "dotnet", variant, checks}));
return failed ? 1 : 0;

sealed class RequestScope : IDisposable {
    public bool Disposed {get; private set;}
    public void Touch() {ObjectDisposedException.ThrowIf(Disposed, this);}
    public void Dispose() {Disposed = true;}
}
sealed class Middle(RequestScope request) { public RequestScope Request {get;} = request; }
sealed class Capture(Middle middle) { public Middle Middle {get;} = middle; }
sealed class Ledger {
    public bool Committed {get; private set;}
    public async Task Commit(CancellationTokenSource cancellation, bool checkBefore, bool checkAfter) {
        if (checkBefore) cancellation.Token.ThrowIfCancellationRequested();
        await Task.CompletedTask;
        Committed = true;
        cancellation.Cancel();
        if (checkAfter) cancellation.Token.ThrowIfCancellationRequested();
    }
}
