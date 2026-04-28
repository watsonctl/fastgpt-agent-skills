import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextResponse } from "next/server";
import { POST } from "@/app/api/rag-helper/${HELPER_NAME}/route";
import { auth } from "@/auth";
import { verifyApiKey } from "@/lib/api-key/verify";

vi.mock("@/auth", () => ({
  auth: vi.fn(),
}));

vi.mock("@/lib/api-key/verify", () => ({
  verifyApiKey: vi.fn(),
}));

describe("POST /api/rag-helper/${HELPER_NAME}", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(auth).mockResolvedValue({ user: { id: "user-1" } } as never);
    vi.mocked(verifyApiKey).mockReturnValue(null);
  });

  it("should return auth error when session is missing and API key is invalid", async () => {
    vi.mocked(auth).mockResolvedValueOnce(null as never);
    vi.mocked(verifyApiKey).mockReturnValueOnce(
      NextResponse.json({ error: "API Key invalid" }, { status: 401 }),
    );

    const response = await POST(
      new Request("http://localhost/api/rag-helper/${HELPER_NAME}", {
        method: "POST",
        body: JSON.stringify({}),
      }),
    );

    expect(response.status).toBe(401);
  });

  it("should return 400 for invalid request bodies", async () => {
    const response = await POST(
      new Request("http://localhost/api/rag-helper/${HELPER_NAME}", {
        method: "POST",
        body: JSON.stringify({}),
      }),
    );

    expect(response.status).toBe(400);
  });
});
