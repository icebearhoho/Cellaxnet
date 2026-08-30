"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Check,
  Loader2,
  Plus,
  RefreshCw,
  ShieldCheck,
  Store,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { setActiveWorkspaceId } from "@/lib/active-workspace";
import { ApiClientError } from "@/lib/api";
import {
  createWorkspace,
  listWorkspaces,
  type SellerWorkspace,
} from "@/lib/workspaces";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const ROLE_LABEL: Record<SellerWorkspace["current_role"], string> = {
  owner: "Chủ sở hữu",
  manager: "Quản lý",
  analyst: "Phân tích",
  viewer: "Chỉ xem",
  platform_admin: "Quản trị nền tảng",
};

const STATUS_LABEL: Record<SellerWorkspace["status"], string> = {
  active: "Hoạt động",
  suspended: "Tạm khóa",
  archived: "Đã lưu trữ",
};

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.envelope.error?.message ?? "Không thể xử lý yêu cầu.";
  }
  return "Không kết nối được máy chủ. Hãy thử lại.";
}

export default function SellerOnboardingPage() {
  const router = useRouter();
  const { user, acceptAccessToken, logout } = useAuth();
  const [workspaces, setWorkspaces] = useState<SellerWorkspace[]>([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    listWorkspaces(controller.signal)
      .then(setWorkspaces)
      .catch((err: unknown) => {
        if (!controller.signal.aborted) setError(errorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const normalizedName = name.trim();
    if (!normalizedName) return;

    setCreating(true);
    setError(null);
    try {
      const result = await createWorkspace(normalizedName);
      acceptAccessToken(result.auth.access_token);
      setWorkspaces((current) => [result.workspace, ...current]);
      setActiveWorkspaceId(result.workspace.id);
      setName("");
      router.push("/seller/workspace");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className="min-h-screen bg-bg px-4 py-8 text-text sm:px-6 lg:py-14">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <Link
            href="/shop"
            className="inline-flex items-center gap-2 text-sm font-medium text-text-muted transition-colors hover:text-text"
          >
            <ArrowLeft className="h-4 w-4" /> Cửa hàng
          </Link>
          <div className="flex items-center gap-3 text-sm text-text-muted">
            <span className="hidden sm:inline">{user?.name || user?.email}</span>
            <button onClick={logout} className="font-medium hover:text-text">
              Đăng xuất
            </button>
          </div>
        </header>

        <section className="mb-8 max-w-3xl">
          <Badge variant="info">Seller workspace</Badge>
          <h1 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
            Thiết lập không gian bán hàng
          </h1>
          <p className="mt-3 text-sm leading-6 text-text-muted sm:text-base">
            Workspace là nơi gom shop, sản phẩm, đơn hàng và thành viên của một đơn vị bán hàng.
            Dữ liệu của mỗi workspace được tách riêng.
          </p>
        </section>

        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <Card className="h-fit">
            <CardHeader>
              <div>
                <CardTitle className="text-base">Workspace của bạn</CardTitle>
                <p className="mt-1 text-xs text-text-muted">
                  {loading ? "Đang tải..." : `${workspaces.length} workspace`}
                </p>
              </div>
              <Store className="h-5 w-5 text-accent" />
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex min-h-28 items-center justify-center text-text-dim">
                  <Loader2 className="h-5 w-5 animate-spin" />
                </div>
              ) : workspaces.length ? (
                <div className="space-y-3">
                  {workspaces.map((workspace) => (
                    <div
                      key={workspace.id}
                      className="rounded-xl border border-border bg-surface-2 p-4"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold">{workspace.name}</div>
                          <div className="mt-1 truncate font-mono text-xs text-text-dim">
                            {workspace.slug}
                          </div>
                        </div>
                        <Badge variant={workspace.status === "active" ? "success" : "warning"}>
                          {STATUS_LABEL[workspace.status]}
                        </Badge>
                      </div>
                      <div className="mt-3 flex items-center gap-2 text-xs text-text-muted">
                        <ShieldCheck className="h-3.5 w-3.5" />
                        {ROLE_LABEL[workspace.current_role]}
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        className="mt-4 w-full"
                        onClick={() => {
                          setActiveWorkspaceId(workspace.id);
                          router.push("/seller/workspace");
                        }}
                      >
                        Vào workspace
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-border p-6 text-center">
                  <Store className="mx-auto h-7 w-7 text-text-dim" />
                  <p className="mt-3 text-sm font-medium">Chưa có workspace</p>
                  <p className="mt-1 text-xs text-text-muted">
                    Tạo workspace đầu tiên để kích hoạt vai trò người bán.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <div>
                  <CardTitle className="text-base">
                    {workspaces.length ? "Tạo workspace khác" : "Tạo workspace đầu tiên"}
                  </CardTitle>
                  <p className="mt-1 text-xs text-text-muted">Ví dụ: Minh Anh Fashion</p>
                </div>
                <Plus className="h-5 w-5 text-accent" />
              </CardHeader>
              <CardContent>
                <form onSubmit={submit} className="space-y-4">
                  <div>
                    <label htmlFor="workspace-name" className="mb-1.5 block text-sm font-medium">
                      Tên đơn vị bán hàng
                    </label>
                    <Input
                      id="workspace-name"
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                      maxLength={100}
                      placeholder="Tên shop hoặc doanh nghiệp"
                    />
                  </div>
                  {error && (
                    <div className="rounded-xl border border-danger/30 bg-danger/5 px-3 py-2 text-xs text-danger">
                      {error}
                    </div>
                  )}
                  <Button type="submit" className="w-full" disabled={creating || !name.trim()}>
                    {creating ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Plus className="h-4 w-4" />
                    )}
                    Tạo workspace
                  </Button>
                </form>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Tiến độ thiết lập</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-3">
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-success/10 text-success">
                    {workspaces.length ? <Check className="h-4 w-4" /> : "1"}
                  </span>
                  <div>
                    <p className="text-sm font-medium">Tạo workspace</p>
                    <p className="mt-0.5 text-xs text-text-muted">Kích hoạt tài khoản người bán.</p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-surface-2 text-xs text-text-muted">
                    2
                  </span>
                  <div>
                    <p className="text-sm font-medium">Kết nối cửa hàng</p>
                    <p className="mt-0.5 text-xs leading-5 text-text-muted">
                      Shopee OAuth sẽ được gắn vào workspace ở bước tích hợp tiếp theo.
                    </p>
                  </div>
                </div>
                <Button variant="outline" className="w-full" disabled>
                  <RefreshCw className="h-4 w-4" /> Kết nối Shopee — sắp có
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </main>
  );
}
