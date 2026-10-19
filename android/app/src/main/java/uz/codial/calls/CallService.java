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

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable sync = () -> CallSync.request(this);
    private final Runnable periodic = new Runnable() {
        @Override
        public void run() {
            CallSync.request(CallService.this);
            handler.postDelayed(this, PERIOD_MS);
        }
    };
    private ContentObserver observer;

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
        handler.postDelayed(periodic, PERIOD_MS);
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
        return START_STICKY;
    }

    private Notification notification() {
        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel(CHANNEL, "Qo'ng'iroqlarni yuborish", NotificationManager.IMPORTANCE_MIN));
        PendingIntent open = PendingIntent.getActivity(this, 0, new Intent(this, MainActivity.class), PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(this, CHANNEL)
                .setSmallIcon(android.R.drawable.sym_call_incoming)
                .setContentTitle("Codial ERP")
                .setContentText("Qo'ng'iroqlar ERP tizimiga yuborilmoqda")
                .setContentIntent(open)
                .setOngoing(true)
                .build();
    }

    @Override
    public void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        if (observer != null) getContentResolver().unregisterContentObserver(observer);
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
