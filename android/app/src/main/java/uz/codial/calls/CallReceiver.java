package uz.codial.calls;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Handler;
import android.os.Looper;
import android.telephony.TelephonyManager;

/** Qo'ng'iroq tugaganda (IDLE) — jurnal yozilishini biroz kutib yuboradi; xizmat to'xtab qolgan bo'lsa qayta yoqadi. */
public class CallReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context ctx, Intent intent) {
        if (!TelephonyManager.EXTRA_STATE_IDLE.equals(intent.getStringExtra(TelephonyManager.EXTRA_STATE))) return;
        Context app = ctx.getApplicationContext();
        PendingResult pending = goAsync();
        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            CallService.start(app);
            CallSync.request(app);
            pending.finish();
        }, 3000);
    }
}
