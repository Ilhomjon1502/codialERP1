package uz.codial.calls;

import android.content.Context;
import android.content.SharedPreferences;

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
    long lastSyncAt() { return sp.getLong("last_sync_at", 0); }
    String lastError() { return sp.getString("last_error", ""); }
    int sentTotal() { return sp.getInt("sent_total", 0); }
    boolean paired() { return !token().isEmpty(); }

    void savePairing(String server, String token, String device, long fromDate) {
        sp.edit().putString("server", server).putString("token", token).putString("device", device)
                .putLong("last_date", fromDate).putString("last_error", "").putInt("sent_total", 0).apply();
    }

    void unpair(String why) {
        sp.edit().putString("token", "").putString("last_error", why).apply();
    }

    void synced(long lastDate, int accepted) {
        sp.edit().putLong("last_date", Math.max(lastDate, lastDate())).putLong("last_sync_at", System.currentTimeMillis())
                .putString("last_error", "").putInt("sent_total", sentTotal() + accepted).apply();
    }

    void error(String why) {
        sp.edit().putString("last_error", why).apply();
    }
}
