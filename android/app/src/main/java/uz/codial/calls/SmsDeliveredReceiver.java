package uz.codial.calls;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.telephony.SmsMessage;

/**
 * Yetkazilish hisoboti (operator qabul qiluvchiga yetganini yoki yetmaganini xabar qiladi). Hamma operator yubormaydi — kelmasa,
 * ERP'da «yetkazilishi noma'lum» turadi. Holat kodi (3GPP): 0 — yetkazildi, 0x20–0x3F — vaqtincha kechikish (yakuniy hisobot keyin keladi),
 * 0x40 va undan katta — yetkazilmadi.
 */
public class SmsDeliveredReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context ctx, Intent intent) {
        String id = intent.getStringExtra("id");
        if (id == null) return;
        boolean ok = getResultCode() == Activity.RESULT_OK;
        String detail = "";
        byte[] pdu = intent.getByteArrayExtra("pdu");
        if (pdu != null) {
            try {
                int st = SmsMessage.createFromPdu(pdu, intent.getStringExtra("format")).getStatus();
                detail = "holat 0x" + Integer.toHexString(st);
                if (st >= 0x20 && st < 0x40) return;  // vaqtincha — yakuniy hisobotni kutamiz
                ok = st == 0;
            } catch (RuntimeException ignored) {
                // pdu o'qilmadi — natija kodiga tayanamiz
            }
        }
        boolean last = intent.getIntExtra("part", 0) >= intent.getIntExtra("total", 1) - 1;
        if (ok && !last) return;
        String base = intent.getStringExtra("info");
        String info = ((base == null ? "" : base) + (detail.isEmpty() ? "" : " · " + detail)).trim();
        String error = ok ? "" : "Qabul qiluvchiga yetmadi (" + (detail.isEmpty() ? "operator xabari" : detail) + ")";
        boolean fOk = ok;
        PendingResult async = goAsync();
        new Thread(() -> {
            try {
                SmsSender.report(ctx.getApplicationContext(), id, fOk, error, "delivered", info);
            } finally {
                async.finish();
            }
        }).start();
    }
}
