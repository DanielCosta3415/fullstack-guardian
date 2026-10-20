using System.Text.Json;
static long AddMinorUnits(long amount, long fee) => checked(amount + fee);
bool overflow = false, cancelled = false;
try { AddMinorUnits(long.MaxValue, 1); } catch (OverflowException) { overflow = true; }
using var cancellation = new CancellationTokenSource();
cancellation.Cancel();
try { await Task.Delay(10000, cancellation.Token); }
catch (OperationCanceledException error) { cancelled = error.CancellationToken == cancellation.Token; }
Console.WriteLine(JsonSerializer.Serialize(new {sum = AddMinorUnits(100, 10), overflow, cancelled}));
