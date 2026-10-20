namespace Iti.AiClient;

public sealed record ChatRequest(
    string Question, 
    string Collection, 
    string? ConversationId = null);

public sealed record ChatResponse(
    string Answer, 
    bool Found, 
    List<Citation> Citations, 
    string ConversationId, 
    string RequestId);

public sealed record Citation(
    string DocId, 
    string Title, 
    int? Page, 
    string Snippet);

public sealed record ChatStreamEvent(
    string? ConversationId,
    string? RequestId,
    string? Text,
    string? Answer,
    bool Found,
    List<Citation>? Citations)
{
    public string Kind { get; init; } = "";
}

public sealed record ConversationSummary(
    string ConversationId,
    string Collection,
    string FirstQuestion, 
    DateTimeOffset CreatedAt);
    
public sealed record MessageOut(
    string Role, 
    string Content, 
    string RequestId, 
    DateTimeOffset CreatedAt,
    List<Citation>? Citations
    );
    
public sealed record Suggestion(
    string Question,
    string File);

public sealed record UploadAccepted(
    string JobId, 
    string DocumentId,
    string Status);
    
public sealed record JobStatus (
    string JobId, 
    string DocumentId, 
    string Filename, 
    string Status,
    int? Chunks,
    string? Error,
    DateTimeOffset CreatedAt,
    DateTimeOffset? FinishedAt);