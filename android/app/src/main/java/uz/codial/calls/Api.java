package uz.codial.calls;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/** ERP API: /api/v1/calls/pair/, /ingest/, /ping/, /sms/outbox/, /sms/report/ (qurilma tokeni bilan, sessiyasiz). */
final class Api {
    static final class HttpError extends IOException {
        final int code;

        HttpError(int code, String message) {
            super(message);
            this.code = code;
        }
    }

    private Api() {}

    static JSONObject request(String server, String path, String token, JSONObject body) throws IOException {
        URL url = new URL(server.replaceAll("/+$", "") + "/api/v1/calls/" + path);
        HttpURLConnection c = (HttpURLConnection) url.openConnection();
        c.setConnectTimeout(15000);
        c.setReadTimeout(30000);
        c.setRequestProperty("Accept", "application/json");
        if (token != null && !token.isEmpty()) c.setRequestProperty("Authorization", "Device " + token);
        // disconnect() chaqirilmaydi: javob to'liq o'qilib yopilsa, ulanish (TLS) keyingi so'rov uchun qayta ishlatiladi —
        // SMS navbati har 30 soniyada so'raladi, har safar yangi TLS ulanish batareya va internetni ko'p yeydi
        if (body != null) {
            c.setRequestMethod("POST");
            c.setDoOutput(true);
            c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            try (OutputStream os = c.getOutputStream()) {
                os.write(body.toString().getBytes(StandardCharsets.UTF_8));
            }
        }
        int code = c.getResponseCode();
        String text = read(code < 400 ? c.getInputStream() : c.getErrorStream());
        JSONObject json;
        try {
            json = text.isEmpty() ? new JSONObject() : new JSONObject(text);
        } catch (JSONException e) {
            json = new JSONObject();
        }
        if (code >= 400) throw new HttpError(code, message(json, code));
        return json;
    }

    private static String message(JSONObject json, int code) {
        if (json.has("detail")) return json.optString("detail");
        if (json.has("code") && json.optJSONArray("code") != null) return json.optJSONArray("code").optString(0);
        return "Server xatosi (" + code + ")";
    }

    private static String read(InputStream in) throws IOException {
        if (in == null) return "";
        try (InputStream is = in; ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buf = new byte[8192];
            int n;
            while ((n = is.read(buf)) > 0) out.write(buf, 0, n);
            return out.toString("UTF-8");
        }
    }
}
