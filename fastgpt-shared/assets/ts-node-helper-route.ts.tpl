import { NextResponse } from "next/server";
import { z } from "zod";
import { auth } from "@/auth";
import { verifyApiKey } from "@/lib/api-key/verify";

const bodySchema = z.object({
  // TODO: replace with the helper's actual request contract
});

export async function POST(request: Request) {
  const session = await auth();
  if (!session?.user) {
    const authError = verifyApiKey(request);
    if (authError) return authError;
  }

  try {
    const parsed = bodySchema.safeParse(await request.json());
    if (!parsed.success) {
      return NextResponse.json(
        {
          error: "Invalid input",
          issues: parsed.error.flatten(),
        },
        { status: 400 },
      );
    }

    return NextResponse.json({
      ok: true,
      helper: "${HELPER_NAME}",
      input: parsed.data,
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: "Internal Server Error",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 500 },
    );
  }
}
