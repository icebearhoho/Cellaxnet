import { useMemo, useState, type ReactNode } from "react";
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import { WebView } from "react-native-webview";
import type { WebViewErrorEvent } from "react-native-webview/lib/WebViewTypes";

const FALLBACK_WEB_URL = "http://192.168.1.64:3000";

function configuredUrl(): URL | null {
  const raw = (process.env.EXPO_PUBLIC_WEB_URL || FALLBACK_WEB_URL).trim();
  try {
    const url = new URL(raw);
    return url.protocol === "http:" || url.protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}

export default function App() {
  const webUrl = useMemo(configuredUrl, []);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const retry = () => {
    setError(null);
    setLoading(true);
    setReloadKey((value) => value + 1);
  };

  const onLoadError = (event: WebViewErrorEvent) => {
    setLoading(false);
    setError(event.nativeEvent.description || "Không thể kết nối tới web local.");
  };

  if (!webUrl) {
    return (
      <Shell>
        <ErrorView
          message="EXPO_PUBLIC_WEB_URL không hợp lệ. Hãy dùng URL bắt đầu bằng http:// hoặc https://."
          url={process.env.EXPO_PUBLIC_WEB_URL || FALLBACK_WEB_URL}
        />
      </Shell>
    );
  }

  return (
    <Shell>
      <WebView
        key={reloadKey}
        source={{ uri: webUrl.toString() }}
        originWhitelist={["http://*", "https://*"]}
        javaScriptEnabled
        domStorageEnabled
        sharedCookiesEnabled
        thirdPartyCookiesEnabled
        allowsBackForwardNavigationGestures
        pullToRefreshEnabled
        setSupportMultipleWindows={false}
        onLoadStart={() => {
          setLoading(true);
          setError(null);
        }}
        onLoadEnd={() => setLoading(false)}
        onError={onLoadError}
        onHttpError={(event) => {
          if (event.nativeEvent.statusCode >= 400) {
            setError(`Web trả về HTTP ${event.nativeEvent.statusCode}.`);
          }
        }}
        style={styles.webView}
      />

      {loading && !error ? (
        <View style={styles.overlay} pointerEvents="none">
          <ActivityIndicator color="#8b5cf6" size="large" />
          <Text style={styles.loadingText}>Đang mở AREA 303…</Text>
        </View>
      ) : null}

      {error ? (
        <View style={styles.overlay}>
          <ErrorView message={error} url={webUrl.toString()} onRetry={retry} />
        </View>
      ) : null}
    </Shell>
  );
}

function Shell({ children }: { children: ReactNode }) {
  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="light" />
      {children}
    </SafeAreaView>
  );
}

function ErrorView({
  message,
  url,
  onRetry,
}: {
  message: string;
  url: string;
  onRetry?: () => void;
}) {
  return (
    <View style={styles.errorCard}>
      <Text style={styles.errorTitle}>Không kết nối được</Text>
      <Text style={styles.errorMessage}>{message}</Text>
      <Text selectable style={styles.url}>{url}</Text>
      <Text style={styles.hint}>
        Kiểm tra iPhone và laptop đang cùng Wi-Fi, rồi xác nhận Next.js đang chạy bằng script local.
      </Text>
      {onRetry ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Thử kết nối lại"
          onPress={onRetry}
          style={({ pressed }) => [styles.retryButton, pressed && styles.retryPressed]}
        >
          <Text style={styles.retryText}>Thử lại</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#080b12" },
  webView: { flex: 1, backgroundColor: "#080b12" },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#080b12",
    padding: 24,
  },
  loadingText: { marginTop: 14, color: "#a8b0c2", fontSize: 14 },
  errorCard: {
    width: "100%",
    maxWidth: 420,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#252b3a",
    backgroundColor: "#111621",
    padding: 22,
  },
  errorTitle: { color: "#f8fafc", fontSize: 22, fontWeight: "700" },
  errorMessage: { marginTop: 10, color: "#fda4af", fontSize: 14, lineHeight: 21 },
  url: {
    marginTop: 14,
    borderRadius: 10,
    backgroundColor: "#080b12",
    color: "#c4b5fd",
    fontSize: 12,
    padding: 10,
  },
  hint: { marginTop: 14, color: "#94a3b8", fontSize: 13, lineHeight: 20 },
  retryButton: {
    alignItems: "center",
    marginTop: 18,
    borderRadius: 12,
    backgroundColor: "#7c3aed",
    paddingHorizontal: 18,
    paddingVertical: 12,
  },
  retryPressed: { opacity: 0.78 },
  retryText: { color: "#ffffff", fontSize: 14, fontWeight: "700" },
});
