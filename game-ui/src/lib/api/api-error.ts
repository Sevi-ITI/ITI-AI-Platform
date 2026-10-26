// FastAPI's one error shape, {"error": {"code", "message"}, "request_id"}, as a plain object that can be
// handed to client components (it never holds the session pass).

export type ApiError = {
  status: number; // 0 = FastAPI could not be reached
  code: string;
  message: string;
  requestId: string | null;
};

export function toApiError(response: Response, body: unknown): ApiError {
  const parsed = body as { error?: { code?: unknown; message?: unknown }; request_id?: unknown } | null;
  const code = parsed?.error?.code;
  const message = parsed?.error?.message;
  const requestId = parsed?.request_id;

  return {
    status: response.status,
    code: typeof code === "string" ? code : "unexpected_response",
    message: typeof message === "string" ? message : `FastAPI answered ${response.status} without the usual error body.`,
    requestId: typeof requestId === "string" ? requestId : response.headers.get("ITI-Request-Id"),
  };
}

export function unreachableError(): ApiError {
  return {
    status: 0,
    code: "api_unreachable",
    message: "The ITI AI service is not reachable. Check that FastAPI is running.",
    requestId: null,
  };
}

/** What to show a person: FastAPI's own message for 4xx; a short generic text (+ request id) otherwise. */
export function displayMessage(error: ApiError): string {
  if (error.status >= 400 && error.status < 500) {
    return error.message;
  }
  if (error.status === 0) {
    return error.message;
  }
  const reference = error.requestId ? ` (request ${error.requestId})` : "";
  return `Something went wrong on the server${reference}. Please try again.`;
}
