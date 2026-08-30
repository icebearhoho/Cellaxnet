const VIRTUAL_TRYON_URL = (
  process.env.VIRTUAL_TRYON_INTERNAL_URL ?? "http://127.0.0.1:7860"
).replace(/\/$/, "");

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function unavailableResponse() {
  return Response.json(
    {
      error:
        "Dịch vụ thử đồ đang tắt. Hãy chạy scripts/start-virtual-tryon.ps1 rồi thử lại.",
    },
    { status: 503 },
  );
}

export async function GET() {
  try {
    const response = await fetch(`${VIRTUAL_TRYON_URL}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5_000),
    });
    if (!response.ok) return unavailableResponse();
    return Response.json(await response.json(), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return unavailableResponse();
  }
}

export async function POST(request: Request) {
  const contentType = request.headers.get("content-type") ?? "";
  if (!contentType.includes("multipart/form-data")) {
    return Response.json(
      { error: "Yêu cầu phải chứa ảnh người mẫu và ảnh trang phục." },
      { status: 400 },
    );
  }

  try {
    const formData = await request.formData();
    if (!(formData.get("person") instanceof File)) {
      return Response.json({ error: "Thiếu ảnh người mẫu." }, { status: 422 });
    }
    if (!(formData.get("garment") instanceof File)) {
      return Response.json({ error: "Thiếu ảnh trang phục." }, { status: 422 });
    }

    const response = await fetch(`${VIRTUAL_TRYON_URL}/api/try-on`, {
      method: "POST",
      body: formData,
      cache: "no-store",
      signal: AbortSignal.timeout(180_000),
    });

    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as
        | { detail?: string }
        | null;
      return Response.json(
        { error: payload?.detail ?? "CatVTON không thể xử lý hai ảnh này." },
        { status: response.status },
      );
    }

    return new Response(await response.arrayBuffer(), {
      status: 200,
      headers: {
        "Content-Type": response.headers.get("content-type") ?? "image/png",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return unavailableResponse();
  }
}
