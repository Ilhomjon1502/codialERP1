package uz.codial.calls;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.database.ContentObserver;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.provider.CallLog;

/**
 * Doimiy (foreground) xizmat: qo'ng'iroqlar jurnali o'zgarishini kuzatadi va qo'ng'iroq tugashi bilan yuboradi.
 * MIUI xizmatni o'chirib qo'ymasligi uchun bildirishnoma doim turadi; qo'shimcha — har 10 daqiqada qayta urinish.
 */
public class CallService extends Service {
    private static final String CHANNEL = "calls";
    private static final long DEBOUNCE_MS = 2500;
    private static final long PERIOD_MS = 10 * 60_000L;
    // SMS navbati: ish vaqtida (8:00–21:00) har 30 soniyada — «Yuborish» bosilgach tez ketsin; tunda har 10 daqiqada (batareya)
    private static final long SMS_POLL_DAY_MS = 30_000L;
    private static final long SMS_POLL_NIGHT_MS = 10 * 60_000L;

    static long smsPollDelay() {
        int h = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY);
        return h >= 8 && h < 21 ? SMS_POLL_DAY_MS : SMS_POLL_NIGHT_MS;
    }

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable sync = () -> CallSync.request(this);
    private final Runnable periodic = new Runnable() {
        @Override
        public void run() {
            CallSync.request(CallService.this);
            SmsInbox.request(CallService.this);
            handler.postDelayed(this, PERIOD_MS);
        }
    };
    private final Runnable smsPoll = new Runnable() {
        @Override
        public void run() {
            SmsSender.request(CallService.this);
            handler.postDelayed(this, smsPollDelay());
        }
    };
    private final Runnable smsIn = () -> SmsInbox.request(this);
    private ContentObserver observer;
    private ContentObserver smsObserver;

    static void start(Context ctx) {
        if (!new Prefs(ctx).paired()) return;
        try {
            ctx.startForegroundService(new Intent(ctx, CallService.class));
        } catch (RuntimeException e) {
            // Android 12+ fonda ishga tushirishni cheklaydi — keyingi job yoki ilova ochilganda boshlanadi
            SyncJob.schedule(ctx);
        }
    }

    @Override
    public void onCreate() {
        super.onCreate();
        observer = new ContentObserver(handler) {
            @Override
            public void onChange(boolean selfChange) {
                handler.removeCallbacks(sync);
                handler.postDelayed(sync, DEBOUNCE_MS);
            }
        };
        try {
            getContentResolver().registerContentObserver(CallLog.Calls.CONTENT_URI, true, observer);
        } catch (SecurityException e) {
            new Prefs(this).error("Qo'ng'iroqlar jurnaliga ruxsat berilmagan");
        }
        smsObserver = new ContentObserver(handler) {
            @Override
            public void onChange(boolean selfChange) {
                handler.removeCallbacks(smsIn);
                handler.postDelayed(smsIn, DEBOUNCE_MS);
            }
        };
        try {
            getContentResolver().registerContentObserver(android.provider.Telephony.Sms.CONTENT_URI, true, smsObserver);
        } catch (SecurityException e) {
            new Prefs(this).smsError("SMS o'qishga ruxsat berilmagan");
        }
        handler.postDelayed(periodic, PERIOD_MS);
        handler.postDelayed(smsPoll, 5000);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Notification n = notification();
        if (Build.VERSION.SDK_INT >= 34) startForeground(1, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
        else startForeground(1, n);
        if (!new Prefs(this).paired()) {
            stopSelf();
            return START_NOT_STICKY;
        }
        CallSync.request(this);
        SmsInbox.request(this);
        return START_STICKY;
    }

    private Notification notification() {
        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel(CHANNEL, "Qo'ng'iroqlarni yuborish", NotificationManager.IMPORTANCE_MIN));
        PendingIntent open = PendingIntent.getActivity(this, 0, new Intent(this, MainActivity.class), PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(this, CHANNEL)
                .setSmallIcon(android.R.drawable.sym_call_incoming)
                .setContentTitle("Codial ERP")
                .setContentText("Qo'ng'iroqlar va SMS — ERP bilan ulangan")
                .setContentIntent(open)
                .setOngoing(true)
                .build();
    }

    @Override
    public void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        if (observer != null) getContentResolver().unregisterContentObserver(observer);
        if (smsObserver != null) getContentResolver().unregisterContentObserver(smsObserver);
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
