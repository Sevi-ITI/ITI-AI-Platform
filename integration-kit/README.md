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
It shows the chat routes your app uses (health, chat, stream, history, suggestions). Press **Authorize**, paste your key,
then **Try it out**; fill in `ITI-User-Id` (required). Each route lists the error codes it can return. The same
description as JSON: `<base URL>v1/openapi.json`. These are real calls: use a test user id, never a real person's.

## How it fits

```
 Browser ──(your login)──► YOUR .NET server ──(HTTPS: ITI-Api-Key + ITI-User-Id)──► ITI AI service
 no key, no user id        key + user id added here                                  answer + citations
```

- The **browser never calls the AI service** and never sees the key.
- Your server sends **who is asking** (`ITI-User-Id`) from its own login session.
- Nothing else is shared: **your database tables don't need to match ours.** The only link is the JSON above.
- **No CORS on the AI service, on purpose.** A browser calling it directly is blocked; that is the wall that keeps
  the key and `ITI-User-Id` out of the page. Your page calls your own server, so CORS never comes up
  (see "Your frontend" below).

## What you get from Vince (ITI AI admin)

- The **base URL**, e.g. `https://ITI-Vinas.ho.intellismartinc.com:8443/` (later a service name such as
  `https://iti-ai-api.ho.intellismartinc.com:8443/`). Your servers must trust ITI's root certificate (pushed
  by IT; on a machine outside the domain, install it into **Local Machine → Trusted Root Certification Authorities**).
- **One API key per app per environment** (dev, prod), and **per company** if your app serves several
  (see "Several companies in one app"). Handed over in person or through a password
  manager. It is shown once; if it's lost or leaked, Vince revokes it and issues a new one.
- The **collections** your key may read (e.g. `iti-docs`) and its **scopes**: `chat:invoke` (ask, read
  history, get suggestion chips). `documents:write` (upload, replace, delete) only if your app manages documents itself; most apps
  only ask, and Vince uploads the policies.

## Setup (3 steps)

**1. Reference the library** in your app's `.csproj` (adjust the path to where you put this folder):

```xml
<ProjectReference Include="..\integration-kit\csharp\Iti.AiClient\Iti.AiClient.csproj" />
```

**2. Configuration.** In `appsettings.json` (no secrets here):

```json
"ItiAi": { "BaseUrl": "https://ITI-Vinas.ho.intellismartinc.com:8443/", "Collection": "iti-docs" }
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

## Several companies in one app

**The API key decides the company.** Each key belongs to one app and one company, and only reads that
company's collections. There is no company field or header: if your app serves several companies, you get
**one key per company**, and your server picks the key from the signed-in person's company.

What the key separates for you: the documents (another company's collection = 403 `collection_forbidden`),
the chats and history (the same user id at two companies is two different people), and the request log.
A conversation id from company A sent with company B's key is a 404 `conversation_not_found`.

**Configuration:** one entry per company, keys again only in environment variables:

```json
"ItiAi": {
  "BaseUrl": "https://ITI-Vinas.ho.intellismartinc.com:8443/",
  "Companies": { "iti": { "Collection": "iti-docs" }, "mayon": { "Collection": "mayon-docs" } }
}
```

```powershell
$env:ItiAi__Keys__iti = "iti_sk_..."
$env:ItiAi__Keys__mayon = "iti_sk_..."
```

**`Program.cs`:** one named client per company, instead of the single `AddHttpClient<ItiAiClient>` above:

```csharp
foreach (var company in builder.Configuration.GetSection("ItiAi:Companies").GetChildren())
{
    builder.Services.AddHttpClient($"iti-ai:{company.Key}", http =>
    {
        http.BaseAddress = new Uri(builder.Configuration["ItiAi:BaseUrl"]!);
        http.Timeout = TimeSpan.FromSeconds(150);
        http.DefaultRequestHeaders.Add("ITI-Api-Key", builder.Configuration[$"ItiAi:Keys:{company.Key}"]);
    });
}
```

**Controller:** take `IHttpClientFactory` instead of `ItiAiClient`, and build the client for each request:

```csharp
public sealed class ChatController(IHttpClientFactory clients, IConfiguration config) : ControllerBase
{
    private string UserId => User.FindFirstValue(ClaimTypes.NameIdentifier)!;
    private string CompanyId => User.FindFirstValue("company_id")!;   // from YOUR login, never from the browser

    // The client and collection for the signed-in person's company. Unknown company = stop, never fall back.
    private (ItiAiClient Ai, string Collection) ForCompany()
    {
        var collection = config[$"ItiAi:Companies:{CompanyId}:Collection"]
            ?? throw new InvalidOperationException($"No ITI AI settings for company '{CompanyId}'.");
        return (new ItiAiClient(clients.CreateClient($"iti-ai:{CompanyId}")), collection);
    }

    [HttpPost("ask")]
    public async Task<IActionResult> Ask(AskBody body, CancellationToken ct)
    {
        var (ai, collection) = ForCompany();
        return Ok(await ai.ChatAsync(UserId, new ChatRequest(body.Question, collection, body.ConversationId), ct: ct));
    }
}
```

Rules for this setup:

- **The company comes from your server's session** (the logged-in person's record), like the user id. Never from
  the browser, a query string or a form field: whoever could change it would read another company's documents.
- **Never fall back to another company's key** when one is missing. Fail and fix the configuration.
- **Store the company with a saved `ConversationId`** if you keep one: a follow-up must use the same company's key.
- Adding a company later: Vince issues its key and collection; you add one `Companies` entry and one environment
  variable. No code change.

## Rules (please read)

1. **The key stays on the server.** Never in JavaScript, never in a page, never in git.
2. **`userId` = the signed-in person's permanent id from your session** (e.g. the user's primary key).
   Never from the browser (people could read each other's chats). Not a username that can be renamed,
   and never reused for a new person. Ideally the same id in all your apps (e.g. the employee number).
   It is **required** on every chat and history call (missing = 422 `invalid_request`).
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
- **New conversation:** leave `ConversationId` out (`null`, the default). Over plain HTTP: leave
  `conversation_id` out or send `null`; a blank `""` also starts a new one.
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

**Suggestion chips** (starter questions on a new chat): `GetSuggestionsAsync(collection)` returns up to 3
(`limit` 1 to 6) `Suggestion(Question, File)`, one per file, picked at random from the collection's indexed
files, so they change between visits. Show them as chips on the new-chat screen only; a click **fills the
question box and does not send**. Reload them when the user picks another collection; an empty list means the
collection has no files yet (show no chips). Same key rules as chat, no `userId` needed. `ChatController.cs`
has a `GET api/assistant/suggestions` example. Today each question reads "What does <file title> cover?";
better generated questions may come later in the same shape, so your code won't change.

**Documents** (only with `documents:write`): see step 5 of `Iti.AiClient.Smoke/Program.cs`:
`UploadDocumentAsync` returns at once, then poll `GetJobAsync` every few seconds until `done` or `failed`.
On `document_exists`, ask the user "Replace the existing file?" and upload again with `replace: true`.
`DeleteDocumentAsync` removes a file and all its versions. PDF only, up to 50 MB.

## Your frontend (the browser part)

The page talks **only to your .NET server**, with the routes from `ChatController.cs` (`[Route("api/assistant")]`).
The person is already signed in to your app, so the browser sends your login cookie, nothing else:

| Page does | Your server route | Body / reply |
|---|---|---|
| ask | `POST /api/assistant/ask` | `{ "question": "...", "conversationId": null }` → `{ answer, found, citations, conversationId, requestId }` |
| ask, word by word | `POST /api/assistant/ask/stream` | same body → one JSON object per line (`meta`, `token`..., `done`) |
| chips | `GET /api/assistant/suggestions` | `[{ question, file }]` |
| refused | any of the above | status 502 / 503 with `{ kind: "error", message, requestId }`: show `message` |

**Ask** (plain JavaScript; the same `fetch` works in React, Angular, Vue):

```js
let conversationId = null;   // keep it for follow-up questions; null = new chat

async function ask(question) {
  const res = await fetch("/api/assistant/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",                        // your login cookie; no key, no user id
    body: JSON.stringify({ question, conversationId }),
  });
  const data = await res.json();
  if (!res.ok) return showError(data.message);         // your own words, from ChatController.Refusal
  conversationId = data.conversationId;
  showAnswer(data.answer, data.found, data.citations); // answer is Markdown; citations: title + page
}
```

**Ask, word by word** (reads the one-object-per-line stream from `AskStream`):

```js
async function askStream(question, box) {
  const res = await fetch("/api/assistant/ask/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ question, conversationId }),
  });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let end;
    while ((end = buffer.indexOf("\n")) >= 0) {        // one JSON object per line
      const line = buffer.slice(0, end);
      buffer = buffer.slice(end + 1);
      if (!line) continue;
      const e = JSON.parse(line);
      if (e.kind === "meta") conversationId = e.conversationId;
      else if (e.kind === "token") box.textContent += e.text;
      else if (e.kind === "done") showAnswer(e.answer, e.found, e.citations);   // REPLACES the tokens
      else if (e.kind === "error") showError(e.message);
    }
  }
}
```

**Frontend on its own dev server** (e.g. Vite on `localhost:5173`, your .NET API on `localhost:5001`): the
browser sees two origins and blocks the call (CORS). Don't add CORS anywhere; let the dev server forward
`/api` to your .NET server, so the page keeps one origin. Vite:

```js
// vite.config.js
export default { server: { proxy: { "/api": { target: "https://localhost:5001", changeOrigin: true, secure: false } } } };
```

(`secure: false` only because it's your own local .NET dev certificate. Angular: `proxy.conf.json`, same idea.)
In production, serve the built page from the same site as your .NET server, or put both behind one address.

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

Expected with a chat-only key: 8 `PASS` lines, one `SKIP  upload checks: this key may not upload (chat only)`
line and `ALL PASSED`. A `FAIL` line names the field or error code.

Only if your key also has `documents:write`: add a company policy PDF you know (never a file with personal data)
as a second argument. The test then also uploads a copy named `kit-smoke-upload.pdf`, waits for indexing and
deletes it again: 11 `PASS` lines.

## Last resort: a demo without your .NET server

Only to prove the connection works (a demo, a first test) **before** your .NET server is ready. Never deployed,
never on a shared machine. The trick is the same dev-server forwarding as above, pointed straight at the AI
service: the dev server (Node, on your PC) adds the key and the user id, so they still never reach the page,
and the page still sees one origin (no CORS).

**Ask Vince first for:** a separate **demo key** (chat only, no tools, revoked after the demo) and your PC's IP
allowed through to port 8443.

**1. `.env.local`** next to `vite.config.js` (git-ignored; **no `VITE_` prefix**, so Vite never puts it in the page):

```
ITI_URL=https://ITI-Vinas.ho.intellismartinc.com:8443
ITI_KEY=iti_sk_...
ITI_DEMO_USER=demo-frontend-1
```

`ITI_DEMO_USER` is a made-up test id, **never a real employee's id**: every visitor of the demo page is that one user.

**2. `vite.config.js`** (demo only):

```js
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "ITI_");   // read by the dev server only, not sent to the page
  return {
    server: {
      host: "localhost",                              // never --host: anyone on the LAN could use your key
      proxy: {
        "/iti": {
          target: env.ITI_URL,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/iti/, ""),
          // lower case ON PURPOSE: browsers send header names in lower case, so these REPLACE whatever the page sends
          headers: { "iti-api-key": env.ITI_KEY, "iti-user-id": env.ITI_DEMO_USER },
        },
      },
    },
  };
});
```

**3. Trust ITI's certificate in Node** (Node ignores the Windows certificate store). Start the dev server with
ITI's root certificate (the `root.crt` IT pushes; ask Vince for the file), never with certificate checks off:

```powershell
$env:NODE_EXTRA_CA_CERTS = "C:\certs\iti-root.crt"
npm run dev
```

**4. Ask from the page.** The AI service's own JSON (snake_case, not your server's camelCase):

```js
const res = await fetch("/iti/v1/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ question: "What is the dress code?", collection: "iti-docs", conversation_id: null }),
});
const data = await res.json();
// ok:      { answer, found, citations: [{ doc_id, title, page, snippet }], conversation_id, request_id }
// refused: { error: { code, message }, request_id }
console.log(res.status, data);
```

**Expected:** `200` with an `answer` and `found: true`. `401 invalid_api_key` = the key in `.env.local`
(the connection itself works). `500` with `http proxy error ... unable to get local issuer certificate` in the dev
server's terminal = step 3 (restart `npm run dev` after setting it); `500` with a timeout or `ECONNREFUSED` there
= port 8443 not open for your PC. `404` = the `/iti` rewrite.

When your .NET server is ready: delete the `/iti` proxy and `.env.local`, switch the page to `/api/assistant/...`,
and tell Vince to revoke the demo key.

## Support and changes

- Problems: send Vince the **`RequestId`** (from the exception or the reply). It finds the call in the
  admin console's request log.
- The contract is **v1** (`openapi-v1.json`). New fields may be added (the library ignores fields it
  doesn't know, so your app keeps working). Renaming or removing anything would be a new `/v2`,
  announced in advance.
- .NET 8 support ends 10 Nov 2026. The library targets `net8.0` and also runs on .NET 10.