import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test";

const apiBase = "http://127.0.0.1:8000";
const headers = { "X-Actor-ID": "demo-user", "X-Scope-Key": "reference-host" };

async function createConversation(
  request: APIRequestContext,
  title: string,
): Promise<string> {
  const response = await request.post(`${apiBase}/v1/assistant/conversations`, {
    headers,
    data: { title },
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()).id;
}

async function openConversation(
  page: Page,
  request: APIRequestContext,
  title: string,
): Promise<string> {
  const id = await createConversation(request, title);
  await page.goto("/");
  await page.getByLabel("Active conversation").selectOption(id);
  return id;
}

async function runThroughApi(
  request: APIRequestContext,
  conversationId: string,
  text: string,
  options: Record<string, string> = {},
): Promise<string> {
  const response = await request.post(
    `${apiBase}/v1/assistant/conversations/${conversationId}/runs`,
    {
      headers,
      data: {
        text,
        attachment_ids: [],
        context_profile: options.context_profile ?? "lite",
        execution_mode: options.execution_mode ?? "confirm_each",
        disclosure_level: options.disclosure_level ?? "status",
      },
    },
  );
  expect(response.ok()).toBeTruthy();
  const run = await response.json();
  const events = await request.get(
    `${apiBase}/v1/assistant/runs/${run.run_id}/events`,
    { headers },
  );
  expect(events.ok()).toBeTruthy();
  const body = await events.text();
  expect(body).toContain("run.completed");
  return body;
}

test("streams a conversation while the Host owns conversation navigation", async ({
  page,
  request,
}) => {
  const firstId = await openConversation(
    page,
    request,
    `Thread A ${Date.now()}`,
  );
  await page
    .getByRole("textbox", { name: "Message" })
    .fill("Hello from the browser");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(
    page
      .locator(".message-user")
      .getByText("Hello from the browser", { exact: true }),
  ).toBeVisible();
  await expect(
    page
      .locator(".message-assistant")
      .getByText(/You said:.*Hello from the browser/),
  ).toBeVisible();

  await page.getByRole("button", { name: "New conversation" }).click();
  await expect(
    page.getByText("Ask a question, attach a file, or propose a Host record."),
  ).toBeVisible();
  await page.getByLabel("Active conversation").selectOption(firstId);
  await expect(
    page
      .locator(".message-user")
      .getByText("Hello from the browser", { exact: true }),
  ).toBeVisible();

  await page.getByLabel("Disclosure level").selectOption("raw_trace");
  await page
    .getByRole("textbox", { name: "Message" })
    .fill("Calculate: 2 + 3 * 4");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("Sensitive provider trace")).toBeVisible();
  await expect(page.getByText("Activity · 1")).toBeVisible();
});

test("keeps attachment, Lightbox, live dictation, and voice-message behavior consistent", async ({
  page,
  request,
}) => {
  const conversationId = await openConversation(
    page,
    request,
    `Multimodal ${Date.now()}`,
  );
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    "base64",
  );
  await page.locator('input[type="file"][multiple]').setInputFiles({
    name: "pixel.png",
    mimeType: "image/png",
    buffer: png,
  });
  await expect(page.getByText("pixel.png", { exact: true })).toBeVisible();
  await page
    .getByRole("textbox", { name: "Message" })
    .fill("Review this image");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(/reviewed 1 attachment/)).toBeVisible();
  await page.getByRole("button", { name: "Open pixel.png" }).click();
  await expect(
    page.getByRole("dialog", { name: "Attachment preview" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close preview" }).click();

  const messageResponse = await request.get(
    `${apiBase}/v1/assistant/conversations/${conversationId}/messages?limit=100`,
    { headers },
  );
  const imageMessage = (await messageResponse.json()).find(
    (message: { role: string }) => message.role === "user",
  );
  const attachmentId = imageMessage.content.find(
    (part: { type: string }) => part.type === "attachment",
  ).attachment_id;
  await runThroughApi(
    request,
    conversationId,
    `Promote attachment: ${attachmentId} | Saved image`,
  );
  const actionResponse = await request.get(
    `${apiBase}/v1/assistant/conversations/${conversationId}/actions`,
    { headers },
  );
  const promotion = (await actionResponse.json()).find(
    (action: { action_type: string }) =>
      action.action_type === "attachment.promote",
  );
  const confirmed = await request.post(
    `${apiBase}/v1/assistant/actions/${promotion.id}/confirm`,
    { headers },
  );
  expect((await confirmed.json()).result.host_resource_ref).toBeTruthy();

  await page.getByLabel("Input mode").selectOption("live_dictation");
  await page.getByRole("button", { name: "Start live dictation" }).click();
  await page.getByRole("button", { name: "Stop live dictation" }).click();
  await expect(page.getByRole("textbox", { name: "Message" })).toHaveValue(
    "Plan a calm weekend trip",
  );

  await page.getByLabel("Input mode").selectOption("voice_message");
  await page.locator('input[type="file"][accept="audio/*"]').setInputFiles({
    name: "voice.webm",
    mimeType: "audio/webm",
    buffer: Buffer.from("reference voice bytes"),
  });
  await expect(page.getByRole("textbox", { name: "Message" })).toHaveValue(
    "Voice message from voice.webm",
  );
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.locator("audio")).toBeVisible();
});

test("confirms and automatically applies typed Host Actions", async ({
  page,
  request,
}) => {
  await openConversation(page, request, `Actions ${Date.now()}`);
  const confirmedTitle = `Groceries ${Date.now()}`;
  await page
    .getByRole("textbox", { name: "Message" })
    .fill(`Create record: ${confirmedTitle} | 42.50`);
  await page.getByRole("button", { name: "Send" }).click();
  await expect(
    page.getByText("awaiting confirmation", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByText("applied", { exact: true })).toBeVisible();
  await expect(
    page.locator(".host-records").getByText(confirmedTitle, { exact: true }),
  ).toBeVisible();

  const automaticTitle = `Transit ${Date.now()}`;
  await page.getByLabel("Execution mode").selectOption("auto_apply_allowlist");
  await page
    .getByRole("textbox", { name: "Message" })
    .fill(`Create record: ${automaticTitle} | 9.75`);
  await page.getByRole("button", { name: "Send" }).click();
  await expect(
    page.getByText("auto_apply_allowlist", { exact: true }),
  ).toBeVisible();
  await expect(
    page.locator(".host-records").getByText(automaticTitle, { exact: true }),
  ).toBeVisible();
});

test("uses one Privacy inventory and one Job detail surface", async ({
  page,
  request,
}) => {
  await openConversation(page, request, `Privacy ${Date.now()}`);
  const memoryText = `window seat ${Date.now()}`;
  await page.getByRole("button", { name: "Memory" }).click();
  await page.getByLabel("Memory content").fill(memoryText);
  await page.getByRole("button", { name: "Remember" }).click();
  const memory = page.getByRole("dialog", { name: "Memory" });
  await expect(
    memory.getByRole("listitem").filter({ hasText: memoryText }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close Memory" }).click();

  await page.getByRole("button", { name: "Privacy" }).click();
  const privacy = page.getByRole("dialog", { name: "Privacy Center" });
  await expect(privacy.getByText("memory", { exact: true })).toBeVisible();
  await privacy.getByLabel(/memory/i).check();
  await privacy.getByRole("button", { name: "Delete selected" }).click();
  await expect(privacy.getByText("Deletion impact")).toBeVisible();
  await privacy.getByRole("button", { name: "Confirm deletion" }).click();
  await expect(privacy.getByText("completed", { exact: true })).toBeVisible();
});

test("runs Context, Retrieval, Generator, and Plugin flows through public HTTP contracts", async ({
  request,
}) => {
  const conversationId = await createConversation(
    request,
    `Contracts ${Date.now()}`,
  );
  const knowledge = await request.post(`${apiBase}/v1/assistant/knowledge`, {
    headers,
    data: {
      title: "Refund policy",
      body: "Refunds are available within thirty days.",
      source_url: "https://example.test/refunds",
    },
  });
  expect(knowledge.ok()).toBeTruthy();

  for (let index = 0; index < 8; index += 1) {
    await runThroughApi(
      request,
      conversationId,
      `Long conversation turn ${index}`,
      { context_profile: "balanced" },
    );
  }
  const manifest = await request.get(
    `${apiBase}/v1/assistant/conversations/${conversationId}/context/manifest?profile=balanced`,
    { headers },
  );
  expect(manifest.ok()).toBeTruthy();
  expect((await manifest.json()).profile).toBe("balanced");

  const sharedMemory = await request.post(`${apiBase}/v1/assistant/memory`, {
    headers,
    data: { scope: "user", content: "Prefers window seats" },
  });
  expect(sharedMemory.ok()).toBeTruthy();
  const secondConversation = await createConversation(
    request,
    `Memory continuity ${Date.now()}`,
  );
  await runThroughApi(request, secondConversation, "Use my saved preference", {
    context_profile: "balanced",
  });
  const secondManifest = await request.get(
    `${apiBase}/v1/assistant/conversations/${secondConversation}/context/manifest?profile=balanced`,
    { headers },
  );
  expect(
    (await secondManifest.json()).blocks.some(
      (block: { kind: string }) => block.kind === "memory",
    ),
  ).toBe(true);

  const retrievalEvents = await runThroughApi(
    request,
    conversationId,
    "Search knowledge: refunds",
    {
      disclosure_level: "activity",
    },
  );
  expect(retrievalEvents).toContain("citation.added");
  const messages = await request.get(
    `${apiBase}/v1/assistant/conversations/${conversationId}/messages?limit=100`,
    { headers },
  );
  expect((await messages.json()).length).toBe(18);

  const generated = await request.post(
    `${apiBase}/v1/assistant/developer/integrations/generate`,
    {
      headers,
      data: {
        application_id: "org.example.generated",
        operations: [
          {
            operation_id: "listItems",
            method: "GET",
            path: "/items",
            side_effect: "read",
          },
          {
            operation_id: "createItem",
            method: "POST",
            path: "/items",
            side_effect: "write-proposal",
          },
        ],
      },
    },
  );
  const generatorResult = await generated.json();
  expect(generatorResult.manifest.review_status).toBe("draft");
  expect(generatorResult.activated).toBe(false);

  await request.patch(`${apiBase}/v1/assistant/plugins/sample.records`, {
    headers,
    data: { enabled: true },
  });
  await runThroughApi(
    request,
    conversationId,
    "Plugin record: plugin-owned proposal",
  );
  let actions = await request.get(
    `${apiBase}/v1/assistant/conversations/${conversationId}/actions`,
    { headers },
  );
  const pluginAction = (await actions.json()).find(
    (action: { plugin_id?: string }) => action.plugin_id === "sample.records",
  );
  await request.patch(`${apiBase}/v1/assistant/plugins/sample.records`, {
    headers,
    data: { enabled: false },
  });
  actions = await request.get(
    `${apiBase}/v1/assistant/conversations/${conversationId}/actions`,
    { headers },
  );
  expect(
    (await actions.json()).find(
      (action: { id: string }) => action.id === pluginAction.id,
    ).state,
  ).toBe("blocked_plugin_disabled");
  await request.patch(`${apiBase}/v1/assistant/plugins/sample.records`, {
    headers,
    data: { enabled: true },
  });
  actions = await request.get(
    `${apiBase}/v1/assistant/conversations/${conversationId}/actions`,
    { headers },
  );
  expect(
    (await actions.json()).find(
      (action: { id: string }) => action.id === pluginAction.id,
    ).state,
  ).toBe("awaiting_confirmation");

  const deniedHeaders = {
    ...headers,
    "X-Denied-Permissions": "host.records.list",
  };
  const deniedRun = await request.post(
    `${apiBase}/v1/assistant/conversations/${conversationId}/runs`,
    {
      headers: deniedHeaders,
      data: {
        text: "List records",
        attachment_ids: [],
        context_profile: "lite",
        execution_mode: "confirm_each",
        disclosure_level: "activity",
      },
    },
  );
  const deniedRunId = (await deniedRun.json()).run_id;
  const deniedEvents = await request.get(
    `${apiBase}/v1/assistant/runs/${deniedRunId}/events`,
    {
      headers: deniedHeaders,
    },
  );
  expect(await deniedEvents.text()).toContain("tool.failed");

  const traceRun = await request.post(
    `${apiBase}/v1/assistant/conversations/${conversationId}/runs`,
    {
      headers,
      data: {
        text: "Trace lifecycle",
        attachment_ids: [],
        context_profile: "lite",
        execution_mode: "confirm_each",
        disclosure_level: "raw_trace",
      },
    },
  );
  const traceRunId = (await traceRun.json()).run_id;
  const liveTrace = await request.get(
    `${apiBase}/v1/assistant/runs/${traceRunId}/events`,
    { headers },
  );
  expect(await liveTrace.text()).toContain("reasoning.trace.delta");
  const replayWithoutTrace = await request.get(
    `${apiBase}/v1/assistant/runs/${traceRunId}/events`,
    { headers },
  );
  expect(await replayWithoutTrace.text()).not.toContain(
    "reasoning.trace.delta",
  );

  const conflictTitle = `Conflict ${Date.now()}`;
  await runThroughApi(
    request,
    conversationId,
    `Create record: ${conflictTitle} | 1.00`,
    {
      execution_mode: "auto_apply_allowlist",
    },
  );
  const records = await request.get(`${apiBase}/v1/assistant/host/records`, {
    headers,
  });
  const record = (await records.json()).find(
    (item: { title: string }) => item.title === conflictTitle,
  );
  await runThroughApi(
    request,
    conversationId,
    `Update record: ${record.id} | Stale update | 2.00 | 999`,
  );
  actions = await request.get(
    `${apiBase}/v1/assistant/conversations/${conversationId}/actions`,
    { headers },
  );
  const staleAction = (await actions.json()).find(
    (action: { action_type: string; payload: { record_id?: string } }) =>
      action.action_type === "host_data.record.update" &&
      action.payload.record_id === record.id,
  );
  const staleConfirmation = await request.post(
    `${apiBase}/v1/assistant/actions/${staleAction.id}/confirm`,
    { headers },
  );
  expect(staleConfirmation.status()).toBe(409);
  const recordsAfterConflict = await request.get(
    `${apiBase}/v1/assistant/host/records`,
    { headers },
  );
  expect(
    (await recordsAfterConflict.json()).find(
      (item: { id: string }) => item.id === record.id,
    ).title,
  ).toBe(conflictTitle);
});
