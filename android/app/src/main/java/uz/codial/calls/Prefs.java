package uz.codial.calls;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/** Sozlamalar: server manzili, qurilma tokeni va oxirgi yuborilgan qo'ng'iroq vaqti. */
final class Prefs {
    static final String DEFAULT_SERVER = "https://erp.codialinfo.uz";

    private final SharedPreferences sp;

    Prefs(Context ctx) {
        sp = ctx.getApplicationContext().getSharedPreferences("codial_calls", Context.MODE_PRIVATE);
    }

    String server() { return sp.getString("server", DEFAULT_SERVER); }
    String token() { return sp.getString("token", ""); }
    String deviceName() { return sp.getString("device", ""); }
    long lastDate() { return sp.getLong("last_date", 0); }
    long lastId() { return sp.getLong("last_id", 0); }
    long lastSyncAt() { return sp.getLong("last_sync_at", 0); }
    String lastError() { return sp.getString("last_error", ""); }
    int sentTotal() { return sp.getInt("sent_total", 0); }
    boolean paired() { return !token().isEmpty(); }

    void savePairing(String server, String token, String device, long fromDate) {
        sp.edit().putString("server", server).putString("token", token).putString("device", device)
                .putLong("last_date", fromDate).putLong("last_id", 0).putLong("sms_in_last_id", 0).putLong("sms_in_from", fromDate)
                .putString("last_error", "").putInt("sent_total", 0).apply();
    }

    void unpair(String why) {
        sp.edit().putString("token", "").putString("last_error", why).apply();
    }

    void synced(long lastDate, long lastId, int accepted) {
        sp.edit().putLong("last_date", Math.max(lastDate, lastDate())).putLong("last_id", Math.max(lastId, lastId()))
                .putLong("last_sync_at", System.currentTimeMillis())
                .putString("last_error", "").putInt("sent_total", sentTotal() + accepted).apply();
    }

    void error(String why) {
        sp.edit().putString("last_error", why).apply();
    }

    long callsFullAt() { return sp.getLong("calls_full_at", 0); }

    void callsFullScanned(long at) {
        sp.edit().putLong("calls_full_at", at).apply();
    }

    // ---------- Kelgan SMS (1.2) ----------
    long smsInLastId() { return sp.getLong("sms_in_last_id", 0); }
    long smsInFullAt() { return sp.getLong("sms_in_full_at", 0); }
    int smsInTotal() { return sp.getInt("sms_in_total", 0); }

    /** Birinchi o'qish qaysi vaqtdan: ulanish kunining boshi (1.2 ga yangilanganda — yangilangan kun boshi). */
    long smsInFrom() {
        long v = sp.getLong("sms_in_from", 0);
        if (v == 0) {
            java.util.Calendar c = java.util.Calendar.getInstance();
            c.set(java.util.Calendar.HOUR_OF_DAY, 0);
            c.set(java.util.Calendar.MINUTE, 0);
            c.set(java.util.Calendar.SECOND, 0);
            c.set(java.util.Calendar.MILLISECOND, 0);
            v = c.getTimeInMillis();
            sp.edit().putLong("sms_in_from", v).apply();
        }
        return v;
    }

    void smsInSynced(long lastId, boolean fullDone) {
        SharedPreferences.Editor e = sp.edit().putLong("sms_in_last_id", Math.max(lastId, smsInLastId()));
        if (fullDone) e.putLong("sms_in_full_at", System.currentTimeMillis());
        e.apply();
    }

    void smsInAccepted(int n) {
        if (n > 0) sp.edit().putInt("sms_in_total", smsInTotal() + n).apply();
    }

    // ---------- SMS (2026-10-22) ----------
    private static final Object LOCK = new Object();

    int smsSentTotal() { return sp.getInt("sms_sent", 0); }
    long smsLastAt() { return sp.getLong("sms_last_at", 0); }
    String smsLastError() { return sp.getString("sms_error", ""); }

    void smsQueued(int n) {
        sp.edit().putLong("sms_last_at", System.currentTimeMillis()).apply();
    }

    void smsSent() {
        synchronized (LOCK) {
            sp.edit().putInt("sms_sent", smsSentTotal() + 1).putString("sms_error", "").putLong("sms_last_at", System.currentTimeMillis()).commit();
        }
    }

    int smsDeliveredTotal() { return sp.getInt("sms_delivered", 0); }

    void smsDelivered() {
        synchronized (LOCK) {
            sp.edit().putInt("sms_delivered", smsDeliveredTotal() + 1).commit();
        }
    }

    /** «Ruxsat berilmagan» va tarmoq xatolari vaqtinchalik — holat tuzalgach ekrandan o'chadi (yuborish xatolari qoladi). */
    void smsClearTransientError() {
        String e = smsLastError();
        if (e.startsWith("SMS yuborishga ruxsat") || e.startsWith("Internet")) smsError("");
    }

    void smsError(String why) {
        sp.edit().putString("sms_error", why == null ? "" : why).apply();
    }

    /** Serverga hali yetkazilmagan yuborish natijalari (internet bo'lmagan payt). */
    JSONArray pendingReports() {
        synchronized (LOCK) {
            try {
                return new JSONArray(sp.getString("sms_reports", "[]"));
            } catch (JSONException e) {
                return new JSONArray();
            }
        }
    }

    void addPendingReport(JSONObject r) {
        synchronized (LOCK) {
            JSONArray a = pendingReports();
            a.put(r);
            sp.edit().putString("sms_reports", a.toString()).commit();
        }
    }

    /** Yuborilgan birinchi `n` tasini o'chiradi (bu orada qo'shilganlari qoladi). */
    void clearPendingReports(int n) {
        synchronized (LOCK) {
            JSONArray a = pendingReports();
            JSONArray rest = new JSONArray();
            for (int i = n; i < a.length(); i++) rest.put(a.opt(i));
            sp.edit().putString("sms_reports", rest.toString()).commit();
        }
    }
}
