import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { NavItem } from "@/lib/nav";

export function ComingSoon({ item }: { item: NavItem }) {
  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Tính năng chưa sẵn sàng</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            {item.label} đang được hoàn thiện và chưa có trong bản trải nghiệm này.
          </p>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-text-muted">
          Bạn có thể quay lại trang chính để dùng các tính năng đang hoạt động.
        </p>
      </CardContent>
    </Card>
  );
}
