package uz.codial.calls;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** Telefon yoqilganda yoki ilova yangilanganda xizmatni qayta ishga tushiradi. */
public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context ctx, Intent intent) {
        SyncJob.schedule(ctx);
        CallService.start(ctx);
    }
}
