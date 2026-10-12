using Iti.AiClient;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHttpClient<ItiAiClient>(http =>
{
    http.BaseAddress = new Uri(builder.Configuration["ItiAi:BaseUrl"]!);
    http.Timeout = TimeSpan.FromSeconds(150);
    http.DefaultRequestHeaders.Add("ITI-Api-Key", builder.Configuration["ItiAi:ApiKey"]);
});

builder.Services.AddControllers();
builder.Services.AddAuthentication();
builder.Services.AddAuthorization();

var app = builder.Build();
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();
app.Run();