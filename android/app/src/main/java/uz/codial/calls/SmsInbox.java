package uz.codial.calls;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.provider.Telephony;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Mijozlardan kelgan SMS (1.2, 2026-10-22): «Kirish qutisi»dan yangi xabarlarni o'qib `POST /api/v1/calls/sms/inbox/` ga yuboradi.
 * Faqat oddiy telefon raqamlaridan (+998 XX XXX XX XX) kelganlar — qisqa raqam va nomli yuboruvchilar (bank kodlari, Click, Payme,
 * operator) telefondan chiqmaydi. Yangilari SMS _ID bo'yicha; sutkada bir marta oxirgi 24 soat qayta yuboriladi (server takrorni
 * qabul qilmaydi). Birinchi marta — shu kunning boshidan.
 */
final class SmsInbox {
    private static final ExecutorService EXEC = Executors.newSingleThreadExecutor();
    private static final int BATCH = 200;

    private SmsInbox() {}

    static boolean allowed(Context ctx) {
        return ctx.checkSelfPermission(Manifest.permission.READ_SMS) == PackageManager.PERMISSION_GRANTED;
    }

    static void request(Context ctx) {
        Context app = ctx.getApplicationContext();
        EXEC.execute(() -> run(app));
    }

    /** Fon oqimida. Natija: server qabul qilganlar soni yoki -1 xato bo'lsa. */
    static synchronized int run(Context ctx) {
        Prefs p = new Prefs(ctx);
        if (!p.paired() || !allowed(ctx)) return 0;
        long now = System.currentTimeMillis();
        long lastId = p.smsInLastId();
        boolean full = lastId > 0 && now - p.smsInFullAt() > CallSync.FULL_SCAN_MS;
        // Birinchi marta (_ID hali yo'q) — shu kun boshidan; sutkada bir marta — oxirgi 24 soat; aks holda faqat yangi _ID'lar
        long dateFrom = lastId == 0 ? p.smsInFrom() : full ? now - CallSync.FULL_SCAN_MS : Long.MAX_VALUE;
        int total = 0;
        try {
            boolean first = true;
            while (true) {
                JSONArray msgs = new JSONArray();
                long[] r = read(ctx, lastId > 0 ? lastId : Long.MAX_VALUE, first ? dateFrom : Long.MAX_VALUE, msgs);
                if (msgs.length() > 0) {
                    JSONObject res = Api.request(p.server(), "sms/inbox/", p.token(), new JSONObject().put("messages", msgs));
                    total += res.optInt("accepted");
                    p.smsInAccepted(res.optInt("accepted"));
                }
                lastId = Math.max(lastId, r[0]);
                p.smsInSynced(lastId, full && first);
                if (r[1] < BATCH) break;
                first = false;  // keyingi to'plam — faqat _ID bo'yicha
            }
            return total;
        } catch (Api.HttpError e) {
            if (e.code == 401) p.unpair("Ulanish bekor qilingan — ERP'dan yangi kod olib qayta ulang");
            else p.smsError(e.getMessage());
            return -1;
        } catch (IOException | JSONException | SecurityException e) {
            p.smsError("Kelgan SMS yuborilmadi: " + e.getMessage());
            return -1;
        }
    }

    /**
     * `_ID > afterId` yoki `DATE > dateFrom` xabarlar (_ID tartibida, ko'pi BATCH ta); oddiy raqamlardan kelganlari `out` ga.
     * Qaytaradi: {ko'rilgan eng katta _ID (filtrdan o'tmaganlari ham — qayta o'qilmasin), ko'rilganlar soni}.
     */
    private static long[] read(Context ctx, long afterId, long dateFrom, JSONArray out) throws JSONException {
        String[] cols = {Telephony.Sms._ID, Telephony.Sms.ADDRESS, Telephony.Sms.DATE, Telephony.Sms.BODY};
        long maxId = 0;
        int seen = 0;
        String where = Telephony.Sms._ID + " > ? OR " + Telephony.Sms.DATE + " > ?";
        try (Cursor c = ctx.getContentResolver().query(Telephony.Sms.Inbox.CONTENT_URI, cols, where,
                new String[]{String.valueOf(afterId), String.valueOf(dateFrom)}, Telephony.Sms._ID + " ASC")) {
            if (c == null) return new long[]{0, 0};
            while (c.moveToNext() && seen < BATCH) {
                seen++;
                maxId = Math.max(maxId, c.getLong(0));
                String address = c.getString(1);
                if (!isPhone(address)) continue;
                String body = c.getString(3);
                out.put(new JSONObject().put("id", c.getLong(0)).put("address", address).put("date", c.getLong(2))
                        .put("body", body == null ? "" : body));
            }
        }
        return new long[]{maxId, seen};
    }

    /** Oddiy O'zbekiston raqami: 9 raqam yoki 998 + 9 raqam (bo'shliq, «+», «-» hisobga olinmaydi); harf bo'lsa — yo'q. */
    static boolean isPhone(String address) {
        if (address == null || address.matches(".*[A-Za-z].*")) return false;
        String d = address.replaceAll("\\D", "");
        return d.length() == 9 || (d.length() == 12 && d.startsWith("998"));
    }
}
