namespace Iti.AiClient;

public sealed class ItiAiException(int status, string code, string message, string? requestId) : Exception(message)
{
    public int Status { get; } = status;
    public string Code { get; } = code;
    public string? RequestId { get; } = requestId;
}

