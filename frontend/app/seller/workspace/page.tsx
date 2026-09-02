"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeftRight,
  Check,
  Loader2,
  LogOut,
  Plus,
  RefreshCw,
  ShieldCheck,
  Store,
  Trash2,
  Users,
} from "lucide-react";
import { readActiveWorkspaceId, setActiveWorkspaceId } from "@/lib/active-workspace";
import { ApiClientError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import {
  addWorkspaceMember,
  disconnectMarketplaceShop,
  listMarketplaceShops,
  listWorkspaceMembers,
  listWorkspaces,
  removeWorkspaceMember,
  updateWorkspaceMemberRole,
  type SellerWorkspace,
  type MarketplaceShop,
  type WorkspaceMember,
} from "@/lib/workspaces";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const ROLE_LABEL: Record<WorkspaceMember["role"], string> = {
  owner: "Chủ sở hữu",
  manager: "Quản lý",
  analyst: "Phân tích",
  viewer: "Chỉ xem",
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

export default function SellerWorkspacePage() {
  const router = useRouter();
  const { user, isAdmin, logout } = useAuth();
  const [workspaces, setWorkspaces] = useState<SellerWorkspace[]>([]);
  const [workspace, setWorkspace] = useState<SellerWorkspace | null>(null);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [shops, setShops] = useState<MarketplaceShop[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"manager" | "analyst" | "viewer">("viewer");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const available = await listWorkspaces();
      const requestedId = readActiveWorkspaceId();
      const selected =
        available.find((item) => item.id === requestedId) ?? available[0] ?? null;
      if (!selected) {
        router.replace("/seller/onboarding");
        return;
      }
      setActiveWorkspaceId(selected.id);
      setWorkspaces(available);
      setWorkspace(selected);
      const [memberRows, shopRows] = await Promise.all([
        listWorkspaceMembers(selected.id),
        listMarketplaceShops(selected.id),
      ]);
      setMembers(memberRows);
      setShops(shopRows);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  const currentMember = useMemo(
    () => members.find((member) => member.user_id === user?.id),
    [members, user?.id],
  );
  const canManage = isAdmin || currentMember?.role === "owner";

  async function selectWorkspace(workspaceId: number) {
    const selected = workspaces.find((item) => item.id === workspaceId);
    if (!selected) return;
    setActiveWorkspaceId(selected.id);
    setWorkspace(selected);
    setMembers([]);
    setShops([]);
    setLoading(true);
    setError(null);
    try {
      const [memberRows, shopRows] = await Promise.all([
        listWorkspaceMembers(selected.id),
        listMarketplaceShops(selected.id),
      ]);
      setMembers(memberRows);
      setShops(shopRows);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function addMember(event: React.FormEvent) {
    event.preventDefault();
    if (!workspace || !email.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const added = await addWorkspaceMember(workspace.id, email.trim(), role);
      setMembers((current) => [...current, added]);
      setEmail("");
      setRole("viewer");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function changeRole(member: WorkspaceMember, nextRole: WorkspaceMember["role"]) {
    if (!workspace || member.role === nextRole) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateWorkspaceMemberRole(workspace.id, member.user_id, nextRole);
      setMembers((current) =>
        current.map((item) => (item.user_id === updated.user_id ? updated : item)),
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function removeMember(member: WorkspaceMember) {
    if (!workspace || !window.confirm(`Xóa ${member.email} khỏi workspace?`)) return;
    setSaving(true);
    setError(null);
    try {
      await removeWorkspaceMember(workspace.id, member.user_id);
      setMembers((current) => current.filter((item) => item.user_id !== member.user_id));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function disconnectShop(shop: MarketplaceShop) {
    if (!workspace || !window.confirm(`Ngắt kết nối shop ${shop.shop_name}?`)) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await disconnectMarketplaceShop(workspace.id, shop.id);
      setShops((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  if (loading && !workspace) {
    return (
      <main className="grid min-h-screen place-items-center bg-bg px-6 text-text-dim">
        <div className="max-w-md text-center">
          <Loader2 className="mx-auto h-6 w-6 animate-spin" />
          <p className="mt-4 text-sm font-medium text-text">Đang mở workspace của bạn…</p>
          <p className="mt-1 text-xs leading-5">
            Máy chủ miễn phí có thể cần vài giây để khởi động. Bạn không cần tải lại trang.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-bg px-4 py-7 text-text sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent/10 text-accent">
              <Store className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <p className="text-xs text-text-dim">Không gian bán hàng</p>
              <h1 className="truncate text-lg font-bold">{workspace?.name}</h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {workspaces.length > 1 && (
              <label className="flex items-center gap-2 rounded-xl border border-border bg-surface px-3 py-2 text-xs">
                <ArrowLeftRight className="h-3.5 w-3.5 text-text-dim" />
                <select
                  aria-label="Chuyển workspace"
                  value={workspace?.id ?? ""}
                  disabled={loading}
                  onChange={(event) => void selectWorkspace(Number(event.target.value))}
                  className="max-w-44 bg-transparent outline-none"
                >
                  {workspaces.map((item) => (
                    <option key={item.id} value={item.id} className="bg-surface">
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <Button asChild variant="outline" size="sm">
              <Link href="/seller/onboarding">Quản lý workspace</Link>
            </Button>
            <Button variant="ghost" size="sm" onClick={logout} title="Đăng xuất">
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </header>

        {error && (
          <div className="mb-6 rounded-xl border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">
            {error}
          </div>
        )}

        {loading && workspace && (
          <div className="mb-6 flex items-center gap-2 rounded-xl border border-border bg-surface px-4 py-3 text-sm text-text-muted">
            <Loader2 className="h-4 w-4 animate-spin" /> Đang tải dữ liệu workspace...
          </div>
        )}

        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="pt-5">
              <p className="text-xs text-text-dim">Trạng thái</p>
              <div className="mt-2 flex items-center gap-2 text-sm font-semibold">
                <Check className={workspace?.status === "active" ? "h-4 w-4 text-success" : "h-4 w-4 text-warning"} />
                {workspace ? STATUS_LABEL[workspace.status] : "Chưa xác định"}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-5">
              <p className="text-xs text-text-dim">Vai trò của bạn</p>
              <div className="mt-2 flex items-center gap-2 text-sm font-semibold">
                <ShieldCheck className="h-4 w-4 text-info" />
                {currentMember ? ROLE_LABEL[currentMember.role] : workspace?.current_role === "platform_admin" ? "Quản trị nền tảng" : "Thành viên"}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-5">
              <p className="text-xs text-text-dim">Thành viên</p>
              <div className="mt-2 flex items-center gap-2 text-sm font-semibold">
                <Users className="h-4 w-4 text-accent" /> {members.length}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mb-6 flex flex-wrap gap-3">
          <Button asChild>
            <Link href="/seller/content-generator">Tạo nội dung sản phẩm</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/seller/seller-coach">Kiểm tra cửa hàng</Link>
          </Button>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
          <Card>
            <CardHeader>
              <div>
                <CardTitle className="text-base">Thành viên workspace</CardTitle>
                <p className="mt-1 text-xs text-text-muted">Quyền truy cập chỉ áp dụng trong workspace này.</p>
              </div>
              <Badge variant="muted">{members.length} người</Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              {members.map((member) => (
                <div key={member.user_id} className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface-2 p-3">
                  <span className="grid h-9 w-9 place-items-center rounded-full bg-accent/10 text-sm font-semibold text-accent">
                    {(member.name || member.email).slice(0, 1).toUpperCase()}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{member.name || member.email}</p>
                    <p className="truncate text-xs text-text-dim">{member.email}</p>
                  </div>
                  {canManage ? (
                    <select
                      aria-label={`Vai trò của ${member.name || member.email}`}
                      value={member.role}
                      disabled={saving}
                      onChange={(event) => void changeRole(member, event.target.value as WorkspaceMember["role"])}
                      className="rounded-lg border border-border bg-surface px-2 py-1.5 text-xs outline-none"
                    >
                      <option value="owner">Chủ sở hữu</option>
                      <option value="manager">Quản lý</option>
                      <option value="analyst">Phân tích</option>
                      <option value="viewer">Chỉ xem</option>
                    </select>
                  ) : (
                    <Badge variant="muted">{ROLE_LABEL[member.role]}</Badge>
                  )}
                  {canManage && member.user_id !== user?.id && (
                    <Button variant="ghost" size="sm" disabled={saving} onClick={() => void removeMember(member)} title="Xóa thành viên">
                      <Trash2 className="h-4 w-4 text-danger" />
                    </Button>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          <div className="space-y-6">
            {canManage && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Thêm thành viên</CardTitle>
                </CardHeader>
                <CardContent>
                  <form onSubmit={addMember} className="space-y-3">
                    <Input aria-label="Email thành viên" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="email@thanhvien.com" required />
                    <select aria-label="Vai trò thành viên mới" value={role} onChange={(event) => setRole(event.target.value as typeof role)} className="h-10 w-full rounded-xl border border-border bg-surface px-3 text-sm outline-none">
                      <option value="manager">Quản lý</option>
                      <option value="analyst">Phân tích</option>
                      <option value="viewer">Chỉ xem</option>
                    </select>
                    <Button type="submit" className="w-full" disabled={saving || !email.trim()}>
                      {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                      Thêm vào workspace
                    </Button>
                  </form>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Kết nối bán hàng</CardTitle>
              </CardHeader>
              <CardContent>
                {shops.length ? (
                  <div className="space-y-3">
                    {shops.map((shop) => {
                      const canManageShop = canManage || currentMember?.role === "manager";
                      return (
                        <div key={shop.id} className="rounded-xl border border-border bg-surface-2 p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="truncate text-sm font-medium">{shop.shop_name}</p>
                              <p className="mt-1 text-xs capitalize text-text-muted">{shop.platform.replace("_", " ")}</p>
                            </div>
                            <Badge variant={shop.status === "connected" ? "success" : shop.status === "revoked" ? "muted" : "warning"}>
                              {shop.status === "connected" ? "Đã kết nối" : shop.status === "revoked" ? "Đã ngắt" : "Cần xử lý"}
                            </Badge>
                          </div>
                          <p className="mt-3 text-xs text-text-dim">
                            Đồng bộ gần nhất: {shop.last_synced_at ? new Date(shop.last_synced_at).toLocaleString("vi-VN") : "Chưa đồng bộ"}
                          </p>
                          {canManageShop && shop.status === "connected" && (
                            <Button variant="ghost" size="sm" className="mt-2 text-danger" disabled={saving} onClick={() => void disconnectShop(shop)}>
                              Ngắt kết nối
                            </Button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed border-border p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium">Shopee</p>
                        <p className="mt-1 text-xs text-text-muted">Chưa kết nối với workspace này.</p>
                      </div>
                      <Badge variant="warning">Chờ kết nối</Badge>
                    </div>
                  </div>
                )}
                <Button variant="outline" className="mt-4 w-full" disabled>
                  <RefreshCw className="h-4 w-4" /> Kết nối Shopee — sắp có
                </Button>
                <p className="mt-3 text-xs leading-5 text-text-dim">
                  Connector cần gửi header X-Workspace-ID; API sẽ tự kiểm tra thành viên và tenant.
                </p>
              </CardContent>
            </Card>

            {isAdmin && (
              <Button asChild className="w-full">
                <Link href="/seller">Mở dashboard quản trị</Link>
              </Button>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
