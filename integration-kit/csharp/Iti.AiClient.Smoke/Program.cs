using Iti.AiClient;

// Smoke test: runs every Iti.AiClient call against a real ITI AI API and prints PASS / FAIL per check.
// The key comes from an environment variable, so it never lands in a file or in the command history:
//   $env:ITI_KIT_KEY = "iti_sk_..."     (an app key with chat:invoke on the collection)
//   dotnet run --project Iti.AiClient.Smoke -- "a question the collection's documents answer"
// A chat-only key runs 8 checks (chat, stream, history, suggestions, errors). With documents:write AND a PDF path as a second
// argument it also runs the 3 upload checks (11 in all):
//   dotnet run --project Iti.AiClient.Smoke -- "a question the PDF answers" "C:\path\to\file.pdf"
// Optional: $env:ITI_KIT_URL (default http://127.0.0.1:8000/), $env:ITI_KIT_COLLECTION (default kit-test).

if (args.Length is < 1 or > 2)
{
    Console.WriteLine("Usage: dotnet run --project Iti.AiClient.Smoke -- \"question\" [\"C:\\path\\to\\file.pdf\"]");
    return 2;
}
var question = args[0];
var pdfPath = args.Length == 2 ? args[1] : null;
var key = Environment.GetEnvironmentVariable("ITI_KIT_KEY");
if (string.IsNullOrWhiteSpace(key))
{
    Console.WriteLine("Set the key first:  $env:ITI_KIT_KEY = \"iti_sk_...\"");
    return 2;
}
var collection = Environment.GetEnvironmentVariable("ITI_KIT_COLLECTION") ?? "kit-test";

// The same three settings a C# app gives AddHttpClient<ItiAiClient>(...) in its Program.cs.
var http = new HttpClient
{
    BaseAddress = new Uri(Environment.GetEnvironmentVariable("ITI_KIT_URL") ?? "http://127.0.0.1:8000/"),
    Timeout = TimeSpan.FromSeconds(150),
};
http.DefaultRequestHeaders.Add("ITI-Api-Key", key);
var ai = new ItiAiClient(http);

const string user = "kit-smoke-user";          // a real app sends the signed-in person's id from its session
const string uploadName = "kit-smoke-upload.pdf";
var failed = 0;

try
{
    // Also tells whether this key may upload: a chat-only key gets scope_forbidden here.
    var cleanup = await Refused(() => ai.DeleteDocumentAsync(collection, uploadName));  // leftover of a halted run
    var canUpload = cleanup is not { Code: "scope_forbidden" };

    // 1. Plain chat
    var chat = await ai.ChatAsync(user, new ChatRequest(question, collection), "smoke test");
    Check(chat.Answer.Length > 0 && chat.ConversationId.StartsWith("iti_conv_") && chat.RequestId.Length > 0,
        "chat: answer, conversation id and request id filled");
    Check(chat.Found && chat.Citations.Any(c => c.Page > 0 && c.Title.Length > 0), "chat: found, with a cited page");

    // 2. Streamed follow-up in the same conversation
    var kinds = new List<string>();
    ChatStreamEvent? meta = null, done = null;
    var follow = new ChatRequest("Summarise that in one sentence.", collection, chat.ConversationId);
    await foreach (var e in ai.ChatStreamAsync(user, follow))
    {
        if (kinds.LastOrDefault() != e.Kind) kinds.Add(e.Kind);
        if (e.Kind == "meta") meta = e;
        if (e.Kind == "done") done = e;
    }
    Check(kinds.FirstOrDefault() == "meta" && kinds.LastOrDefault() == "done", $"stream: {string.Join(" -> ", kinds)}");
    Check(meta?.ConversationId == chat.ConversationId && done?.Answer?.Length > 0, "stream: same conversation, final answer filled");

    // 3. History
    var conversations = await ai.GetConversationsAsync(user);
    Check(conversations.Any(c => c.ConversationId == chat.ConversationId && c.CreatedAt > DateTimeOffset.UtcNow.AddHours(-1)),
        "history: conversation listed, created just now (UTC)");
    var messages = await ai.GetMessagesAsync(user, chat.ConversationId);
    Check(string.Join(",", messages.Select(m => m.Role)) == "user,assistant,user,assistant" && messages[1].Citations is not null,
        "history: 4 messages in order, citations saved");

    // 4. Suggestion chips: at most 3, each about a different file
    var chips = await ai.GetSuggestionsAsync(collection);
    Check(chips.Count is > 0 and <= 3 && chips.All(c => c.Question.EndsWith('?') && c.File.Length > 0)
        && chips.Select(c => c.File).Distinct().Count() == chips.Count, $"suggestions: {chips.Count} chips, one per file");

    // 5. Upload, wait for indexing, refuse a duplicate, delete (only with documents:write and a PDF path)
    if (!canUpload || pdfPath is null)
    {
        Console.WriteLine(canUpload ? "SKIP  upload checks: no PDF path given" : "SKIP  upload checks: this key may not upload (chat only)");
    }
    else
    {
        await using (var pdf = File.OpenRead(pdfPath))
        {
            var accepted = await ai.UploadDocumentAsync(collection, pdf, uploadName);
            var job = await ai.GetJobAsync(accepted.JobId);
            while (job.Status is "queued" or "running")
            {
                await Task.Delay(TimeSpan.FromSeconds(2));
                job = await ai.GetJobAsync(accepted.JobId);
            }
            Check(job is { Status: "done", Chunks: > 0 }, $"upload: indexed ({job.Chunks} chunks) {job.Error}");
        }
        var again = await Refused(async () =>
        {
            await using var pdf = File.OpenRead(pdfPath);
            await ai.UploadDocumentAsync(collection, pdf, uploadName);
        });
        Check(again is { Status: 409, Code: "document_exists" }, "upload again: document_exists (409)");
        await ai.DeleteDocumentAsync(collection, uploadName);
        var gone = await Refused(() => ai.DeleteDocumentAsync(collection, uploadName));
        Check(gone is { Code: "document_not_found" }, "delete: file gone");
    }

    // 6. A collection this key may not use
    var forbidden = await Refused(() => ai.ChatAsync(user, new ChatRequest(question, "kit-smoke-forbidden")));
    Check(forbidden is { Status: 403, Code: "collection_forbidden", RequestId: not null },
        "errors: collection_forbidden (403) with a request id");
}
catch (ItiAiException ex)
{
    Check(false, $"API refused: {ex.Code} ({ex.Status}) {ex.Message} request_id={ex.RequestId}");
}
catch (HttpRequestException ex)
{
    Check(false, $"cannot reach the API: {ex.Message}");
}

Console.WriteLine(failed == 0 ? "ALL PASSED" : $"{failed} FAILED");
return failed == 0 ? 0 : 1;

void Check(bool ok, string what)
{
    Console.WriteLine($"{(ok ? "PASS" : "FAIL")}  {what}");
    if (!ok) failed++;
}

static async Task<ItiAiException?> Refused(Func<Task> call)
{
    try
    {
        await call();
        return null;
    }
    catch (ItiAiException ex)
    {
        return ex;
    }
}