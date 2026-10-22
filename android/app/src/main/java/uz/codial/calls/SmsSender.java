package uz.codial.calls;

import android.Manifest;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.PowerManager;
import android.telephony.SmsManager;
import android.telephony.SubscriptionInfo;
import android.telephony.SubscriptionManager;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * SMS navbati (2026-10-22): ERP'da administrator «Yuborish»ni bosgan to'lov eslatmalarini serverdan olib, shu telefonning SIM'idan yuboradi.
 * Server bergan xabar «Yuborilmoqda» bo'ladi — qayta berilmaydi. Natija (yuborildi / xato) {@link SmsSentReceiver} orqali qaytariladi;
 * internet bo'lmasa natija saqlanib, keyingi urinishda yuboriladi. Operator spam deb to'xtatmasligi uchun xabarlar orasida pauza.
 */
final class SmsSender {
    static final String ACTION_SENT = "uz.codial.calls.SMS_SENT";
    static final String ACTION_DELIVERED = "uz.codial.calls.SMS_DELIVERED";
    private static final ExecutorService EXEC = Executors.newSingleThreadExecutor();
    private static final AtomicBoolean BUSY = new AtomicBoolean(false);
    private static final long PAUSE_MS = 4000;
    private static final int MAX_ROUNDS = 10;

    private SmsSender() {}

    /** Har 30 soniyada chaqiriladi; yuborish davom etayotgan bo'lsa (pauzalar bilan bir necha daqiqa) — yangisi navbatga qo'shilmaydi. */
    static void request(Context ctx) {
        Context app = ctx.getApplicationContext();
        if (!BUSY.compareAndSet(false, true)) return;
        EXEC.execute(() -> {
            try {
                run(app);
            } finally {
                BUSY.set(false);
            }
        });
    }

    static boolean allowed(Context ctx) {
        return ctx.checkSelfPermission(Manifest.permission.SEND_SMS) == PackageManager.PERMISSION_GRANTED;
    }

    /** Fon oqimida. Natija: yuborishga berilgan SMS soni yoki -1 xato bo'lsa. */
    static synchronized int run(Context ctx) {
        Prefs p = new Prefs(ctx);
        if (!p.paired()) return 0;
        flushReports(ctx);
        if (!allowed(ctx)) {
            p.smsError("SMS yuborishga ruxsat berilmagan");
            return -1;
        }
        p.smsClearTransientError();  // ruxsat bor — «ruxsat berilmagan» degan eski yozuv o'chadi
        int total = 0;
        PowerManager.WakeLock lock = null;
        try {
            for (int round = 0; round < MAX_ROUNDS; round++) {
                JSONArray msgs = Api.request(p.server(), "sms/outbox/", p.token(), null).optJSONArray("messages");
                p.smsClearTransientError();
                if (msgs == null || msgs.length() == 0) break;
                if (lock == null) {  // yuborish (pauzalar bilan) davomida ekran o'chiq bo'lsa ham protsessor uxlamasin
                    lock = ctx.getSystemService(PowerManager.class).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "codial:sms");
                    lock.acquire(15 * 60_000L);
                }
                for (int i = 0; i < msgs.length(); i++) {
                    JSONObject m = msgs.getJSONObject(i);
                    send(ctx, m.getString("id"), m.getString("phone"), m.getString("text"));
                    total++;
                    Thread.sleep(PAUSE_MS);
                }
            }
            if (total > 0) p.smsQueued(total);
            return total;
        } catch (Api.HttpError e) {
            if (e.code == 401) p.unpair("Ulanish bekor qilingan — ERP'dan yangi kod olib qayta ulang");
            else p.smsError(e.getMessage());
            return -1;
        } catch (IOException | JSONException e) {
            p.smsError("Internet yoki server bilan aloqa yo'q: " + e.getMessage());
            return -1;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return total;
        } finally {
            if (lock != null && lock.isHeld()) lock.release();
        }
    }

    private static void send(Context ctx, String id, String phone, String text) {
        String info = "";
        try {
            // Tizimdagi «SMS uchun SIM» aniq ko'rsatiladi; qaysi SIM va operator ekani ERP'da ko'rinadi
            int subId = SubscriptionManager.getDefaultSmsSubscriptionId();
            SmsManager sm = Build.VERSION.SDK_INT >= 31 ? ctx.getSystemService(SmsManager.class) : SmsManager.getDefault();
            if (subId != SubscriptionManager.INVALID_SUBSCRIPTION_ID) {
                sm = Build.VERSION.SDK_INT >= 31 ? sm.createForSubscriptionId(subId) : SmsManager.getSmsManagerForSubscriptionId(subId);
            }
            info = simInfo(ctx, subId);
            ArrayList<String> parts = sm.divideMessage(text);
            ArrayList<PendingIntent> sent = new ArrayList<>();
            ArrayList<PendingIntent> delivered = new ArrayList<>();
            for (int i = 0; i < parts.size(); i++) {
                sent.add(resultIntent(ctx, SmsSentReceiver.class, ACTION_SENT, id, i, parts.size(), info));
                delivered.add(resultIntent(ctx, SmsDeliveredReceiver.class, ACTION_DELIVERED, id, i, parts.size(), info));
            }
            if (parts.size() == 1) sm.sendTextMessage(phone, null, text, sent.get(0), delivered.get(0));
            else sm.sendMultipartTextMessage(phone, null, parts, sent, delivered);
        } catch (RuntimeException e) {  // SecurityException, IllegalArgumentException — darhol xato
            report(ctx, id, false, "Telefon yubora olmadi: " + e.getMessage(), "sent", info);
        }
    }

    /** Operator natijasi qaytadigan intent. MUTABLE: tizim `errorCode` (yuborish xatosi) va `pdu` (yetkazilish holati) ni shu intentga qo'shadi. */
    private static PendingIntent resultIntent(Context ctx, Class<?> receiver, String action, String id, int part, int total, String info) {
        Intent i = new Intent(ctx, receiver).setAction(action)
                .putExtra("id", id).putExtra("part", part).putExtra("total", total).putExtra("info", info);
        int flags = PendingIntent.FLAG_ONE_SHOT | (Build.VERSION.SDK_INT >= 31 ? PendingIntent.FLAG_MUTABLE : 0);
        return PendingIntent.getBroadcast(ctx, (action + id + "#" + part).hashCode(), i, flags);
    }

    private static String simInfo(Context ctx, int subId) {
        try {
            SubscriptionManager sub = ctx.getSystemService(SubscriptionManager.class);
            SubscriptionInfo si = sub.getActiveSubscriptionInfo(subId);
            int count = sub.getActiveSubscriptionInfoCount();
            if (si == null) return "SIM aniqlanmadi";
            return "SIM " + (si.getSimSlotIndex() + 1) + " · " + si.getCarrierName() + (count > 1 ? " (" + count + " SIM)" : "");
        } catch (RuntimeException e) {
            return "";
        }
    }

    /** Natijani serverga yuboradi; internet bo'lmasa saqlab qo'yadi (keyingi `run` da qayta). stage: "sent" yoki "delivered". */
    static void report(Context ctx, String id, boolean ok, String error, String stage, String info) {
        Prefs p = new Prefs(ctx);
        try {
            p.addPendingReport(new JSONObject().put("id", id).put("ok", ok).put("error", error == null ? "" : error)
                    .put("stage", stage).put("info", info == null ? "" : info));
        } catch (JSONException ignored) {
            return;
        }
        if ("delivered".equals(stage)) {
            if (ok) p.smsDelivered();
        } else if (ok) {
            p.smsSent();
        } else {
            p.smsError(error);
        }
        flushReports(ctx);
    }

    private static final Object REPORT_LOCK = new Object();

    static void flushReports(Context ctx) {
        synchronized (REPORT_LOCK) {
            flushLocked(ctx);
        }
    }

    private static void flushLocked(Context ctx) {
        Prefs p = new Prefs(ctx);
        JSONArray pending = p.pendingReports();
        if (pending.length() == 0 || !p.paired()) return;
        try {
            Api.request(p.server(), "sms/report/", p.token(), new JSONObject().put("results", pending));
            p.clearPendingReports(pending.length());
        } catch (IOException | JSONException ignored) {
            // keyingi urinishda
        }
    }
}
