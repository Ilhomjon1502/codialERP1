package uz.codial.calls;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.telephony.SmsManager;

/** SMS yuborish natijasi (operatorga ketdimi). Ko'p bo'lakli SMS'da — oxirgi bo'lak yoki birinchi xato bo'yicha. */
public class SmsSentReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context ctx, Intent intent) {
        String id = intent.getStringExtra("id");
        if (id == null) return;
        boolean ok = getResultCode() == Activity.RESULT_OK;
        boolean last = intent.getIntExtra("part", 0) >= intent.getIntExtra("total", 1) - 1;
        if (ok && !last) return;
        String error = ok ? "" : reason(getResultCode());
        PendingResult async = goAsync();
        new Thread(() -> {
            try {
                SmsSender.report(ctx.getApplicationContext(), id, ok, error);
            } finally {
                async.finish();
            }
        }).start();
    }

    private static String reason(int code) {
        switch (code) {
            case SmsManager.RESULT_ERROR_RADIO_OFF: return "Aloqa o'chiq (parvoz rejimi)";
            case SmsManager.RESULT_ERROR_NO_SERVICE: return "Tarmoq yo'q";
            case SmsManager.RESULT_ERROR_NULL_PDU: return "Xabar yaratilmadi";
            case SmsManager.RESULT_ERROR_LIMIT_EXCEEDED: return "SMS limiti — telefonda ruxsat bering";
            case SmsManager.RESULT_ERROR_SHORT_CODE_NOT_ALLOWED:
            case SmsManager.RESULT_ERROR_SHORT_CODE_NEVER_ALLOWED: return "Telefon ruxsat bermadi";
            default: return "Operator qabul qilmadi (kod " + code + ") — balans yoki SMS paketini tekshiring";
        }
    }
}
