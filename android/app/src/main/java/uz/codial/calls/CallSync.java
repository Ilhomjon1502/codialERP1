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
 * Yangi qatorlar CallLog _ID bo'yicha olinadi (1.1): kechikib yozilgan qator (masalan, suhbat paytidagi javobsiz qo'ng'iroq)
 * ham katta _ID oladi, shuning uchun har safar faqat yangilari yuboriladi; zaxira — oxirgi 10 daqiqa sana bo'yicha.
 * Server takrorni qabul qilmaydi (qurilma + id + vaqt). 1.0 dan yangilanganda bir marta eskicha 3 soatlik oyna bilan o'qiladi.
 * Internet bo'lmasa — keyingi urinishda (qo'ng'iroq tugaganda, har 10 daqiqada, har 15 daqiqalik job'da) yuboriladi.
 */
final class CallSync {
    private static final ExecutorService EXEC = Executors.newSingleThreadExecutor();
    private static final long OVERLAP_MS = 3 * 3600_000L;
    private static final long OVERLAP_SHORT_MS = 10 * 60_000L;
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
            long lastId = p.lastId();
            // Yangi qatorlar _ID bo'yicha (kech yozilgan qator ham katta _ID oladi); sana bo'yicha qisqa oyna — zaxira.
            // 1.0 dan yangilanganda (_ID hali yo'q) — eskicha 3 soatlik oyna bir marta.
            long dateFrom = Math.max(0, p.lastDate() - (lastId > 0 ? OVERLAP_SHORT_MS : OVERLAP_MS));
            boolean first = true;
            while (true) {
                JSONArray calls = new JSONArray();
                long[] max = read(ctx, lastId > 0 ? lastId : Long.MAX_VALUE, first ? dateFrom : Long.MAX_VALUE, calls);
                if (calls.length() == 0) {
                    p.synced(p.lastDate(), lastId, 0);
                    break;
                }
                JSONObject body = new JSONObject().put("calls", calls).put("app_version", version(ctx));
                JSONObject res = Api.request(p.server(), "ingest/", p.token(), body);
                int accepted = res.optInt("accepted");
                total += accepted;
                lastId = Math.max(lastId, max[0]);
                p.synced(max[1], lastId, accepted);
                if (calls.length() < BATCH) break;
                first = false;  // keyingi to'plam — faqat _ID bo'yicha
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

    /** `_ID > afterId` yoki `DATE > dateFrom` qatorlar (_ID tartibida). Qaytaradi: {eng katta _ID, eng katta sana}. */
    private static long[] read(Context ctx, long afterId, long dateFrom, JSONArray out) throws JSONException {
        String[] cols = {CallLog.Calls._ID, CallLog.Calls.NUMBER, CallLog.Calls.TYPE, CallLog.Calls.DATE, CallLog.Calls.DURATION,
                CallLog.Calls.CACHED_NAME, CallLog.Calls.PHONE_ACCOUNT_ID};
        long maxId = 0;
        long max = 0;
        String where = CallLog.Calls._ID + " > ? OR " + CallLog.Calls.DATE + " > ?";
        try (Cursor c = ctx.getContentResolver().query(CallLog.Calls.CONTENT_URI, cols, where,
                new String[]{String.valueOf(afterId), String.valueOf(dateFrom)}, CallLog.Calls._ID + " ASC")) {
            if (c == null) return new long[]{maxId, max};
            while (c.moveToNext() && out.length() < BATCH) {
                long date = c.getLong(3);
                maxId = Math.max(maxId, c.getLong(0));
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
        return new long[]{maxId, max};
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
