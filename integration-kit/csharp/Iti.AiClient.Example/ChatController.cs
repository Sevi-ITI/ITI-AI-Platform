using System.Security.Claims;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace Iti.AiClient.Example;

// The browser talks to YOUR server; only your server talks to the ITI AI API.
// So the browser never sees the API key and never chooses whose chat it is.
[ApiController]
[Authorize]
[Route("api/assistant")]
public sealed class ChatController(ItiAiClient ai, IConfiguration config, ILogger<ChatController> log) : ControllerBase
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    public sealed record AskBody(string Question, string? ConversationId);

    // The signed-in person's PERMANENT id from your login (e.g. the MySQL user's primary key).
    // Not User.Identity.Name: a renamed username would lose the person's history.
    private string UserId => User.FindFirstValue(ClaimTypes.NameIdentifier)!;

    private string Collection => config["ItiAi:Collection"]!;

    [HttpPost("ask")]
    public async Task<IActionResult> Ask(AskBody body, CancellationToken ct)
    {
        try
        {
            return Ok(await ai.ChatAsync(UserId, new ChatRequest(body.Question, Collection, body.ConversationId), ct: ct));
        }
        catch (ItiAiException ex)
        {
            var (status, error) = Refusal(ex);
            return StatusCode(status, error);
        }
    }

    // One JSON object per line: {"kind":"meta",...} {"kind":"token","text":"..."} ... {"kind":"done","answer":"...",...}
    // or a last {"kind":"error","message":"...","requestId":"..."}. The page appends tokens and replaces them with "answer".
    [HttpPost("ask/stream")]
    public async Task AskStream(AskBody body, CancellationToken ct)
    {
        Response.ContentType = "application/x-ndjson";
        try
        {
            var request = new ChatRequest(body.Question, Collection, body.ConversationId);
            await foreach (var e in ai.ChatStreamAsync(UserId, request, ct: ct))
            {
                await Response.WriteAsync(JsonSerializer.Serialize(e, Json) + "\n", ct);
                await Response.Body.FlushAsync(ct);  // send each token now, not at the end
            }
        }
        catch (ItiAiException ex)
        {
            var (status, error) = Refusal(ex);
            if (!Response.HasStarted) Response.StatusCode = status;
            await Response.WriteAsync(JsonSerializer.Serialize(error, Json) + "\n", ct);
        }
    }

    // Log the code and request id (never the question); show the user your own words.
    private (int Status, object Error) Refusal(ItiAiException ex)
    {
        log.LogWarning("ITI AI refused: {Code} ({Status}) request_id={RequestId}", ex.Code, ex.Status, ex.RequestId);
        var busy = ex.Code == "llm_busy";
        var message = busy ? "The assistant is busy. Please try again in a minute." : "The assistant is unavailable right now.";
        return (busy ? 503 : 502, new { kind = "error", message, requestId = ex.RequestId });
    }
}