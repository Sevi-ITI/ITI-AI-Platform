# ITI AI: integration kit for .NET apps

The ITI AI service answers questions **only from ITI's uploaded documents**, cites the file and page,
and says "I don't know" when the documents don't contain the answer. Your app calls it over HTTPS
with its own API key. This folder has everything you need:

| Path | What |
|---|---|
| `csharp/Iti.AiClient/` | The client library (`net8.0`, no NuGet packages). Reference it from your app |
| `csharp/Iti.AiClient.Example/` | How a web app wires it: `Program.cs` (setup) and `ChatController.cs` (plain + streamed chat) |
| `csharp/Iti.AiClient.Smoke/` | A test that runs every call against the real service. Run it first |
| `openapi-v1.json` | The v1 contract (every route, field and error). The library follows it |

**Interactive API docs (Swagger):** `<base URL>v1/docs`, e.g. `https://ITI-Vinas.ho.intellismartinc.com:8443/v1/docs`.
It shows the chat routes your app uses (health, chat, stream, history). Press **Authorize**, paste your key,
then **Try it out**; fill in `ITI-User-Id` (required, although the page marks it optional). The same
description as JSON: `<base URL>v1/openapi.json`. These are real calls: use a test user id, never a real person's.

## How it fits

```
 Browser ──(your login)──► YOUR .NET server ──(HTTPS: ITI-Api-Key + ITI-User-Id)──► ITI AI service
 no key, no user id        key + user id added here                                  answer + citations
```

- The **browser never calls the AI service** and never sees the key.
- Your server sends **who is asking** (`ITI-User-Id`) from its own login session.
- Nothing else is shared: **your database tables don't need to match ours.** The only link is the JSON above.

## What you get from Vince (ITI AI admin)

- The **base URL**, e.g. `https://ITI-Vinas.ho.intellismartinc.com:8443/` (later a service name such as
  `https://iti-ai-api.ho.intellismartinc.com:8443/`). Your servers must trust ITI's root certificate (pushed
  by IT; on a machine outside the domain, install it into **Local Machine → Trusted Root Certification Authorities**).
- **One API key per app per environment** (dev, prod). Handed over in person or through a password
  manager. It is shown once; if it's lost or leaked, Vince revokes it and issues a new one.
- The **collections** your key may read (e.g. `iti-docs`) and its **scopes**: `chat:invoke` (ask and read
  history). `documents:write` (upload, replace, delete) only if your app manages documents itself; most apps
  only ask, and Vince uploads the policies.

## Setup (3 steps)

**1. Reference the library** in your app's `.csproj` (adjust the path to where you put this folder):

```xml
<ProjectReference Include="..\integration-kit\csharp\Iti.AiClient\Iti.AiClient.csproj" />
```

**2. Configuration.** In `appsettings.json` (no secrets here):

```json
"ItiAi": { "BaseUrl": "https://ai.iti.local/", "Collection": "iti-docs" }
```

The **key** goes only in an environment variable on the server (or your secret store), never in
`appsettings.json` or git. ASP.NET Core maps it to `ItiAi:ApiKey` by itself:

```powershell
$env:ItiAi__ApiKey = "iti_sk_..."      # double underscore
```

**3. Register the client** in `Program.cs`, exactly as in `Iti.AiClient.Example/Program.cs`:

```csharp
builder.Services.AddHttpClient<ItiAiClient>(http =>
{
    http.BaseAddress = new Uri(builder.Configuration["ItiAi:BaseUrl"]!);  // keep the trailing slash
    http.Timeout = TimeSpan.FromSeconds(150);                             // answers can queue for 120 s
    http.DefaultRequestHeaders.Add("ITI-Api-Key", builder.Configuration["ItiAi:ApiKey"]);
});
```

Then ask for `ItiAiClient` in any controller's constructor (see `ChatController.cs`).

## Rules (please read)

1. **The key stays on the server.** Never in JavaScript, never in a page, never in git.
2. **`userId` = the signed-in person's permanent id from your session** (e.g. the user's primary key).
   Never from the browser (people could read each other's chats). Not a username that can be renamed,
   and never reused for a new person. Ideally the same id in all your apps (e.g. the employee number).
   It is **required** on every chat and history call (missing = 422 `invalid_request`), even though
   Swagger (`/docs`) shows the `ITI-User-Id` header as optional.
3. **Timeout of at least 150 s.** One model serves everyone; questions can wait in a queue.
4. **Retry only `llm_busy`**, once, after a pause. Never retry anything else automatically.
5. **Log `Code` and `RequestId`, never the question** (it may contain personal details).
6. **Show users that chats are recorded** (the wording comes from ITI's Data Protection Officer).

## Using it

```csharp
var r = await ai.ChatAsync(userId, new ChatRequest("How many leave days do new employees get?", collection));
// r.Answer (Markdown), r.Found, r.Citations (DocId, Title, Page, Snippet), r.ConversationId, r.RequestId
```

- **`Answer` is Markdown** (lists, bold, tables): render it as Markdown.
- **`Found = false` is the "I don't know" reply.** Show it like any answer; it is not an error.
- **`Found = true` with no citations:** show "No source cited, please verify with HR".
- **Citations:** show the file title and page. `Snippet` is the start of the passage, not an exact quote.
- **Follow-up questions:** send the previous `ConversationId` in the next `ChatRequest`. Store it if you
  want "continue this chat" (it fits `VARCHAR(32)`). That is the only column you might add.
- **History:** `GetConversationsAsync(userId)` (newest first) and `GetMessagesAsync(userId, conversationId)`.
  Users only ever see their own.
- **Times are UTC** (`DateTimeOffset`). Convert to Manila time only for display.

**Streaming** (the answer appears word by word): `ChatStreamAsync` returns events in this order:

| `Kind` | Fields | What to do |
|---|---|---|
| `meta` | `ConversationId`, `RequestId` | keep the conversation id |
| `token` (many) | `Text` | append to the screen |
| `done` | `Answer`, `Found`, `Citations` | **replace** the shown text with `Answer` (it can differ from the tokens) |

A failure during the stream throws `ItiAiException` like any other call. `ChatController.cs` shows
how to pass the stream to the browser (one JSON object per line). If you host on IIS, make sure
response buffering/compression doesn't hold the stream back, or tokens arrive all at once.

**Documents** (only with `documents:write`): see step 4 of `Iti.AiClient.Smoke/Program.cs`:
`UploadDocumentAsync` returns at once, then poll `GetJobAsync` every few seconds until `done` or `failed`.
On `document_exists`, ask the user "Replace the existing file?" and upload again with `replace: true`.
`DeleteDocumentAsync` removes a file and all its versions. PDF only, up to 50 MB.

## Errors

Every refusal throws **`ItiAiException`** with `Status`, `Code`, `Message` and `RequestId`.
Branch on `Code`, not on `Status`.

| Status | Code | Meaning | What to do |
|---|---|---|---|
| 401 | `invalid_api_key` | key wrong, revoked or expired | alert your ops, contact Vince |
| 403 | `scope_forbidden` / `collection_forbidden` | the key may not do this | configuration: contact Vince |
| 404 | `collection_not_found`, `conversation_not_found`, `document_not_found`, `job_not_found` | doesn't exist (or isn't this user's) | check the id |
| 409 | `document_exists` | same file name already indexed | ask "Replace?", resend with `replace: true` |
| 409 | `upload_in_progress` | that file is being indexed | try again in a minute |
| 413 | `file_too_large` | over 50 MB | |
| 415 | `unsupported_file_type` | not a PDF | |
| 422 | `invalid_request` | e.g. missing user id, question over 4,000 characters | fix the call |
| 503 | `llm_busy` | queue full | **retry once** after a pause, or "try again in a minute" |
| 503 | `llm_unavailable` | the model is down | "Assistant unavailable", no retry |
| 500 | `internal_error` | a bug on the AI side | send Vince the `RequestId`, no retry |
| 0 | any | the error arrived during a stream | same handling as above |
| 5xx | `http_<status>` | not from the AI service (e.g. a proxy) | ops / Vince |

## Check your setup: the smoke test

From `csharp\`, with your key and the collection Vince gives you, and a question its documents answer:

```powershell
$env:ITI_KIT_KEY = "iti_sk_..."
$env:ITI_KIT_URL = "https://ITI-Vinas.ho.intellismartinc.com:8443/"
$env:ITI_KIT_COLLECTION = "iti-docs"
dotnet run --project Iti.AiClient.Smoke -- "What is the dress code?"
```

Expected with a chat-only key: 7 `PASS` lines, one `SKIP  upload checks: this key may not upload (chat only)`
line and `ALL PASSED`. A `FAIL` line names the field or error code.

Only if your key also has `documents:write`: add a company policy PDF you know (never a file with personal data)
as a second argument. The test then also uploads a copy named `kit-smoke-upload.pdf`, waits for indexing and
deletes it again: 10 `PASS` lines.

## Support and changes

- Problems: send Vince the **`RequestId`** (from the exception or the reply). It finds the call in the
  admin console's request log.
- The contract is **v1** (`openapi-v1.json`). New fields may be added (the library ignores fields it
  doesn't know, so your app keeps working). Renaming or removing anything would be a new `/v2`,
  announced in advance.
- .NET 8 support ends 10 Nov 2026. The library targets `net8.0` and also runs on .NET 10.