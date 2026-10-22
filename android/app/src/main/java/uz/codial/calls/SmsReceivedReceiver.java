package uz.codial.calls;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Handler;
import android.os.Looper;

/** SMS kelganda — kirish qutisiga yozilishini biroz kutib ERP'ga yuboradi; xizmat to'xtab qolgan bo'lsa qayta yoqadi. */
public class SmsReceivedReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context ctx, Intent intent) {
        Context app = ctx.getApplicationContext();
        PendingResult pending = goAsync();
        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            CallService.start(app);
            SmsInbox.request(app);
            pending.finish();
        }, 3000);
    }
}
