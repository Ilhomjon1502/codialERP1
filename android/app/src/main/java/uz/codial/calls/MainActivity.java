package uz.codial.calls;

import android.Manifest;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.provider.DocumentsContract;
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
    private static final char LF = (char) 10;
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
        root.addView(text("Bu telefondagi qo'ng'iroqlar tugashi bilan ERP tizimidagi «Qo'ng'iroqlar» bo'limiga yuboriladi: raqam, vaqt va davomiylik. "
                + "Suhbat yozuvini bu ilovaning o'zi yozmaydi — telefondagi yozuvchi ilova saqlagan fayllar ERP'ga yuklanadi (4-band). "
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

        root.addView(header("4. Suhbat yozuvlari"));
        root.addView(text("Yozuvchi ilova (masalan ShizuCallRecorder) suhbatlarni shu telefonda alohida papkaga saqlasin. "
                + "Papkani shu yerda tanlang — undagi yangi audio fayllar har qo'ng'iroqdan keyin ERP'ga yuklanadi va mos qo'ng'iroqqa biriktiriladi. "
                + "Papka tanlashda «Yangi papka» yarating (masalan «Yozuvlar»); Download yoki xotira ildizini Android ruxsat bermaydi.", 13));
        root.addView(button("Yozuvlar papkasini tanlash", v -> pickRecordingsFolder()));
        root.addView(button("Yozuvlarni hozir yuklash", v -> uploadRecordingsNow()));
        root.addView(button("Papkani uzish", v -> {
            prefs.recSetTree(null);
            refresh();
        }));
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
        if (!prefs.smsLastError().isEmpty()) s.append("❗ SMS: ").append(prefs.smsLastError()).append(LF);
        if (prefs.recTree() == null) s.append("Yozuvlar papkasi tanlanmagan — suhbat yozuvlari ERP'ga yuklanmaydi");
        else {
            s.append("✅ Yozuvlar papkasi: ").append(folderName(prefs.recTree())).append(" · yuklandi ").append(prefs.recUploaded()).append(" ta");
            if (prefs.recLastAt() > 0) s.append(" · oxirgi ").append(fmt(prefs.recLastAt()));
            if (!prefs.recLastError().isEmpty()) s.append(LF).append("❗ Yozuv: ").append(prefs.recLastError());
        }
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

    private static String folderName(Uri tree) {
        String id = DocumentsContract.getTreeDocumentId(tree);
        int i = id.indexOf(':');
        return i >= 0 && i < id.length() - 1 ? id.substring(i + 1) : id;
    }

    private void pickRecordingsFolder() {
        if (!prefs.paired()) {
            toast("Avval ERP'ga ulang");
            return;
        }
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION | Intent.FLAG_GRANT_PREFIX_URI_PERMISSION);
        try {
            startActivityForResult(i, 2);
        } catch (ActivityNotFoundException e) {
            toast("Telefonda papka tanlash oynasi topilmadi");
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != 2 || resultCode != RESULT_OK || data == null || data.getData() == null) return;
        Uri tree = data.getData();
        try {
            getContentResolver().takePersistableUriPermission(tree, Intent.FLAG_GRANT_READ_URI_PERMISSION);
        } catch (SecurityException e) {
            toast("Bu papkaga ruxsat olib bo'lmadi — boshqa papka tanlang");
            return;
        }
        prefs.recSetTree(tree);
        toast("Papka tanlandi. Bundan keyingi yozuvlar yuklanadi");
        CallService.start(this);
        refresh();
    }

    private void uploadRecordingsNow() {
        if (prefs.recTree() == null) {
            toast("Avval yozuvlar papkasini tanlang");
            return;
        }
        BG.execute(() -> {
            int n = Recordings.run(this);
            ui.post(() -> {
                toast(n < 0 ? "Yuklanmadi: " + prefs.recLastError() : "Yuklandi: " + n + " ta yozuv");
                refresh();
            });
        });
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
