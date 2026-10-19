package uz.codial.calls;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.provider.CallLog;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Qo'ng'iroqlar jurnalidan oxirgi yuborilgandan keyingilarini o'qib serverga yuboradi.
 * Server takrorni qabul qilmaydi (qurilma + id + vaqt), shuning uchun 3 soatlik «ustma-ust» oyna bilan o'qiladi —
 * kechikib yozilgan qatorlar (masalan, suhbat paytidagi javobsiz qo'ng'iroq) ham tushib qolmaydi.
 * Internet bo'lmasa — keyingi urinishda (qo'ng'iroq tugaganda, har 10 daqiqada, har 15 daqiqalik job'da) yuboriladi.
 */
final class CallSync {
    private static final ExecutorService EXEC = Executors.newSingleThreadExecutor();
    private static final long OVERLAP_MS = 3 * 3600_000L;
    private static final int BATCH = 200;

    private CallSync() {}

    static void request(Context ctx) {
        Context app = ctx.getApplicationContext();
        EXEC.execute(() -> run(app));
    }

    /** Sinxron (fon oqimida chaqiriladi). Natija: yuborilganlar soni yoki -1 xato bo'lsa. */
    static synchronized int run(Context ctx) {
        Prefs p = new Prefs(ctx);
        if (!p.paired()) return 0;
        if (ctx.checkSelfPermission(Manifest.permission.READ_CALL_LOG) != PackageManager.PERMISSION_GRANTED) {
            p.error("Qo'ng'iroqlar jurnaliga ruxsat berilmagan");
            return -1;
        }
        int total = 0;
        try {
            long from = Math.max(0, p.lastDate() - OVERLAP_MS);
            while (true) {
                JSONArray calls = new JSONArray();
                long maxDate = read(ctx, from, calls);
                if (calls.length() == 0) {
                    p.synced(p.lastDate(), 0);
                    break;
                }
                JSONObject body = new JSONObject().put("calls", calls).put("app_version", version(ctx));
                JSONObject res = Api.request(p.server(), "ingest/", p.token(), body);
                int accepted = res.optInt("accepted");
                total += accepted;
                p.synced(maxDate, accepted);
                if (calls.length() < BATCH) break;
                from = maxDate;  // keyingi to'plam
            }
            return total;
        } catch (Api.HttpError e) {
            if (e.code == 401) p.unpair("Ulanish bekor qilingan — ERP'dan yangi kod olib qayta ulang");
            else p.error(e.getMessage());
            return -1;
        } catch (IOException | JSONException | SecurityException e) {
            p.error("Internet yoki server bilan aloqa yo'q: " + e.getMessage());
            return -1;
        }
    }

    private static long read(Context ctx, long from, JSONArray out) throws JSONException {
        String[] cols = {CallLog.Calls._ID, CallLog.Calls.NUMBER, CallLog.Calls.TYPE, CallLog.Calls.DATE, CallLog.Calls.DURATION,
                CallLog.Calls.CACHED_NAME, CallLog.Calls.PHONE_ACCOUNT_ID};
        long max = from;
        try (Cursor c = ctx.getContentResolver().query(CallLog.Calls.CONTENT_URI, cols, CallLog.Calls.DATE + " > ?",
                new String[]{String.valueOf(from)}, CallLog.Calls.DATE + " ASC")) {
            if (c == null) return max;
            while (c.moveToNext() && out.length() < BATCH) {
                long date = c.getLong(3);
                out.put(new JSONObject()
                        .put("id", c.getLong(0))
                        .put("number", nz(c.getString(1)))
                        .put("type", c.getInt(2))
                        .put("date", date)
                        .put("duration", c.getLong(4))
                        .put("name", nz(c.getString(5)))
                        .put("sim", nz(c.getString(6))));
                max = Math.max(max, date);
            }
        }
        return max;
    }

    private static String nz(String s) {
        return s == null ? "" : s;
    }

    static String version(Context ctx) {
        try {
            return ctx.getPackageManager().getPackageInfo(ctx.getPackageName(), 0).versionName;
        } catch (PackageManager.NameNotFoundException e) {
            return "";
        }
    }
}
