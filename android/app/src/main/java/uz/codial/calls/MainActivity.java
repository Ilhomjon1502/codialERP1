package uz.codial.calls;

import android.Manifest;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.provider.Settings;
import android.text.InputType;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.Executors;

/** Bitta ekran: ulash (server + 8 belgili kod), holat, ruxsatlar va MIUI sozlamalari. */
public class MainActivity extends Activity {
    private static final java.util.concurrent.ExecutorService BG = Executors.newSingleThreadExecutor();  // har bosishda yangi oqim ochilmasin
    private final Handler ui = new Handler(Looper.getMainLooper());
    private Prefs prefs;
    private LinearLayout root;
    private TextView status;
    private EditText server;
    private EditText code;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = new Prefs(this);
        ScrollView scroll = new ScrollView(this);
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(16);
        root.setPadding(pad, pad, pad, pad);
        scroll.addView(root);
        setContentView(scroll);
        build();
    }

    @Override
    protected void onResume() {
        super.onResume();
        refresh();
        if (prefs.paired()) {
            CallService.start(this);
            SyncJob.schedule(this);
        }
    }

    private void build() {
        TextView title = text("Codial ERP — qo'ng'iroqlar", 20);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        root.addView(title);
        root.addView(text("Bu telefondagi qo'ng'iroqlar tugashi bilan ERP tizimidagi «Qo'ng'iroqlar» bo'limiga yuboriladi. "
                + "Suhbat yozib olinmaydi — faqat raqam, vaqt va davomiylik. "
                + "ERP'da administrator «SMS yuborish»ni bossa, to'lov eslatmalari shu telefonning SIM kartasidan yuboriladi. "
                + "Mijozlardan (oddiy raqamlardan) kelgan SMS'lar ERP'ga tushadi; bank va xizmat SMS'lari yuborilmaydi.", 14));

        status = text("", 15);
        status.setPadding(0, dp(12), 0, dp(12));
        root.addView(status);

        root.addView(header("1. Ruxsatlar"));
        root.addView(button("Ruxsatlarni berish", v -> askPermissions()));
        root.addView(button("Batareya tejashni o'chirish", v -> batteryExemption()));
        root.addView(button("MIUI: Avtozapusk (Autostart) yoqish", v -> miuiAutostart()));
        root.addView(text("Xiaomi/Redmi'da: Sozlamalar → Ilovalar → Codial qo'ng'iroqlar → «Avtozapusk» yoqilgan, "
                + "«Batareya tejash» → «Cheklovlarsiz» bo'lsin. Oxirgi ilovalar ro'yxatida ilovani qulflab qo'ying (🔒).", 13));

        root.addView(header("2. ERP'ga ulash"));
        server = new EditText(this);
        server.setText(prefs.server());
        server.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        root.addView(label("Server manzili"));
        root.addView(server);
        code = new EditText(this);
        code.setHint("Masalan: ABCD-2345");
        code.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS);
        root.addView(label("Ulash kodi (ERP → Qo'ng'iroqlar → Qurilmalar)"));
        root.addView(code);
        root.addView(button("Ulash", v -> pair()));

        root.addView(header("3. Tekshirish"));
        root.addView(button("Hozir yuborish", v -> syncNow()));
        root.addView(text("SMS ko'p yuborilganda Android «Ilova ko'p SMS yuboryapti» deb so'rashi mumkin — «Doim ruxsat berish» ni belgilab, «Yuborish»ni bosing.", 13));
    }

    private void refresh() {
        StringBuilder s = new StringBuilder();
        s.append(prefs.paired() ? "✅ Ulangan: " + prefs.deviceName() : "⚠️ ERP'ga ulanmagan").append('\n');
        s.append(hasCallLog() ? "✅ Qo'ng'iroqlar jurnaliga ruxsat bor" : "⚠️ Qo'ng'iroqlar jurnaliga ruxsat yo'q").append('\n');
        PowerManager pm = getSystemService(PowerManager.class);
        s.append(pm.isIgnoringBatteryOptimizations(getPackageName()) ? "✅ Batareya tejash o'chirilgan" : "⚠️ Batareya tejash yoqilgan — ilova to'xtab qolishi mumkin").append('\n');
        if (prefs.lastSyncAt() > 0) s.append("Oxirgi yuborish: ").append(fmt(prefs.lastSyncAt())).append(" · jami ").append(prefs.sentTotal()).append(" ta\n");
        if (!prefs.lastError().isEmpty()) s.append("❗ ").append(prefs.lastError()).append('\n');
        s.append(SmsSender.allowed(this) ? "✅ SMS yuborishga ruxsat bor" : "⚠️ SMS yuborishga ruxsat yo'q — to'lov eslatmalari ketmaydi").append('\n');
        if (prefs.smsLastAt() > 0) {
            s.append("SMS: yuborildi ").append(prefs.smsSentTotal()).append(" · yetkazildi ").append(prefs.smsDeliveredTotal())
                    .append(" · oxirgi ").append(fmt(prefs.smsLastAt())).append('\n');
        }
        s.append(SmsInbox.allowed(this) ? "✅ Kelgan SMS'larni o'qishga ruxsat bor" : "⚠️ SMS o'qishga ruxsat yo'q — mijozlardan kelgan SMS ERP'ga tushmaydi").append('\n');
        if (prefs.smsInTotal() > 0) s.append("Kelgan SMS: jami ").append(prefs.smsInTotal()).append(" ta ERP'ga yuborildi\n");
        if (!prefs.smsLastError().isEmpty()) s.append("❗ SMS: ").append(prefs.smsLastError());
        status.setText(s.toString().trim());
    }

    private boolean hasCallLog() {
        return checkSelfPermission(Manifest.permission.READ_CALL_LOG) == PackageManager.PERMISSION_GRANTED;
    }

    private void askPermissions() {
        List<String> need = new ArrayList<>();
        need.add(Manifest.permission.READ_CALL_LOG);
        need.add(Manifest.permission.READ_PHONE_STATE);
        need.add(Manifest.permission.SEND_SMS);
        need.add(Manifest.permission.READ_SMS);
        need.add(Manifest.permission.RECEIVE_SMS);
        if (Build.VERSION.SDK_INT >= 33) need.add(Manifest.permission.POST_NOTIFICATIONS);
        requestPermissions(need.toArray(new String[0]), 1);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        refresh();
        if (prefs.paired() && hasCallLog()) {
            CallService.start(this);
            CallSync.request(this);
        }
        if (prefs.paired() && SmsSender.allowed(this)) SmsSender.request(this);
        if (prefs.paired() && SmsInbox.allowed(this)) SmsInbox.request(this);
    }

    private void batteryExemption() {
        try {
            startActivity(new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:" + getPackageName())));
        } catch (ActivityNotFoundException e) {
            openAppSettings();
        }
    }

    private void miuiAutostart() {
        try {
            Intent i = new Intent();
            i.setComponent(new ComponentName("com.miui.securitycenter", "com.miui.permcenter.autostart.AutoStartManagementActivity"));
            startActivity(i);
        } catch (ActivityNotFoundException | SecurityException e) {
            openAppSettings();
        }
    }

    private void openAppSettings() {
        startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + getPackageName())));
    }

    private void pair() {
        String srv = server.getText().toString().trim();
        String c = code.getText().toString().trim();
        if (c.isEmpty()) {
            toast("Ulash kodini kiriting");
            return;
        }
        if (!hasCallLog()) {
            toast("Avval ruxsatlarni bering");
            askPermissions();
            return;
        }
        BG.execute(() -> {
            try {
                JSONObject body = new JSONObject().put("code", c).put("app_version", CallSync.version(this));
                JSONObject res = Api.request(srv, "pair/", null, body);
                String device = res.getJSONObject("device").optString("name") + " (" + res.getJSONObject("device").optString("branch") + ")";
                prefs.savePairing(srv, res.getString("token"), device, startOfToday());
                ui.post(() -> {
                    code.setText("");
                    toast("Ulandi! Bugungi qo'ng'iroqlar yuborilmoqda");
                    SyncJob.schedule(this);
                    CallService.start(this);
                    refreshLater();
                });
            } catch (Exception e) {
                ui.post(() -> toast("Ulanmadi: " + e.getMessage()));
            }
        });
    }

    private void syncNow() {
        if (!prefs.paired()) {
            toast("Avval ERP'ga ulang");
            return;
        }
        BG.execute(() -> {
            int n = CallSync.run(this);
            ui.post(() -> {
                toast(n < 0 ? "Yuborilmadi: " + prefs.lastError() : "Yuborildi: " + n + " ta yangi qo'ng'iroq");
                refresh();
            });
        });
    }

    private void refreshLater() {
        refresh();
        ui.postDelayed(this::refresh, 4000);
    }

    private static long startOfToday() {
        Calendar c = Calendar.getInstance();
        c.set(Calendar.HOUR_OF_DAY, 0);
        c.set(Calendar.MINUTE, 0);
        c.set(Calendar.SECOND, 0);
        c.set(Calendar.MILLISECOND, 0);
        return c.getTimeInMillis();
    }

    private static String fmt(long ms) {
        return new SimpleDateFormat("dd.MM.yyyy HH:mm", Locale.US).format(new Date(ms));
    }

    private void toast(String s) {
        Toast.makeText(this, s, Toast.LENGTH_LONG).show();
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    private TextView text(String s, int sp) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(sp);
        t.setPadding(0, dp(4), 0, dp(4));
        return t;
    }

    private TextView header(String s) {
        TextView t = text(s, 17);
        t.setTypeface(Typeface.DEFAULT_BOLD);
        t.setPadding(0, dp(18), 0, dp(4));
        return t;
    }

    private TextView label(String s) {
        TextView t = text(s, 13);
        t.setPadding(0, dp(8), 0, 0);
        return t;
    }

    private Button button(String s, View.OnClickListener l) {
        Button b = new Button(this);
        b.setText(s);
        b.setAllCaps(false);
        b.setOnClickListener(l);
        return b;
    }
}
