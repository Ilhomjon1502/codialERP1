package uz.codial.calls;

import android.content.Context;
import android.database.Cursor;
import android.media.MediaMetadataRetriever;
import android.net.Uri;
import android.provider.DocumentsContract;

import org.json.JSONObject;

import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Suhbat yozuvlari (1.4). Ilovaning o'zi suhbatni yozmaydi: telefondagi yozuvchi ilova (masalan ShizuCallRecorder)
 * fayllarni tanlangan papkaga saqlaydi, bu yerda esa shu papka kuzatiladi va yangi fayllar ERP'ga yuklanadi.
 * Mos qo'ng'iroqni server vaqt bo'yicha topadi (fayl o'zgargan vaqt + davomiylik). Qo'ng'iroq jurnaldan hali kelmagan bo'lsa,
 * server «pending» deydi va fayl keyingi urinishda qayta yuboriladi (3 kungacha).
 */
final class Recordings {
    private static final ExecutorService EXEC = Executors.newSingleThreadExecutor();
    private static final long SETTLE_MS = 15_000L;          // fayl yopilishi uchun: oxirgi o'zgarishdan 15 soniya o'tgan bo'lsin
    private static final long GIVE_UP_MS = 3 * 86_400_000L; // mos qo'ng'iroq 3 kunda topilmasa — tashlanadi
    private static final int MAX_FILES = 3000;
    private static final int MAX_DEPTH = 3;
    private static final String[] EXT = {".m4a", ".aac", ".mp3", ".ogg", ".opus", ".oga", ".wav", ".amr", ".3gp", ".flac", ".mp4", ".webm"};

    // Yozuvchi ilova fayl nomiga qo'ng'iroq raqamini yozadi: 20261118_115420.745+0500_out_+998901234567.ogg
    // Vaqt zonasi (+0500) raqam emas: raqamni «_out_» / «_in_» dan keyingi qismdan olamiz, bo'lmasa — oxirgi 9–15 raqamli guruhdan
    private static final Pattern NUMBER_AFTER_DIR = Pattern.compile("_(?:out|in|incoming|outgoing)_(\\+?\\d{7,15})", Pattern.CASE_INSENSITIVE);
    private static final Pattern ANY_NUMBER = Pattern.compile("(\\+?\\d{9,15})");

    private Recordings() {}

    /** Fayl nomidagi telefon raqami yoki "" (yashirin raqam, nomda raqam yo'q). */
    static String numberFromName(String name) {
        Matcher m = NUMBER_AFTER_DIR.matcher(name);
        if (m.find()) return m.group(1);
        String last = "";
        Matcher a = ANY_NUMBER.matcher(name.replaceFirst("^\\d{8}_\\d{6}(?:\\.\\d+)?[+-]\\d{4}", ""));
        while (a.find()) last = a.group(1);
        return last;
    }

    static boolean enabled(Context ctx) {
        return new Prefs(ctx).paired() && new Prefs(ctx).recTree() != null;
    }

    static void request(Context ctx) {
        Context app = ctx.getApplicationContext();
        EXEC.execute(() -> run(app));
    }

    private static final class Item {
        String docId, name;
        long modified, size;
        Uri uri;

        String sig() {
            try {
                MessageDigest md = MessageDigest.getInstance("SHA-256");
                byte[] d = md.digest((docId + "|" + size + "|" + modified).getBytes("UTF-8"));
                StringBuilder sb = new StringBuilder();
                for (int i = 0; i < 20; i++) sb.append(String.format(Locale.US, "%02x", d[i]));
                return sb.toString();
            } catch (Exception e) {
                return docId + "|" + size + "|" + modified;
            }
        }
    }

    /** Sinxron (fon oqimida). Natija: yuklanganlar soni, xato bo'lsa -1. */
    static synchronized int run(Context ctx) {
        Prefs p = new Prefs(ctx);
        Uri tree = p.recTree();
        if (!p.paired() || tree == null) return 0;
        // avval qo'ng'iroqlar jurnali yuboriladi — server yozuvni shu yozuvlarga moslaydi
        CallSync.run(ctx);
        List<Item> found = new ArrayList<>();
        try {
            scan(ctx, tree, DocumentsContract.getTreeDocumentId(tree), 0, found);
        } catch (SecurityException e) {
            p.recError("Papkaga ruxsat yo'q — papkani qayta tanlang");
            return -1;
        } catch (RuntimeException e) {
            p.recError("Papkani o'qib bo'lmadi: " + e.getMessage());
            return -1;
        }
        long now = System.currentTimeMillis();
        long since = p.recSince();
        int sent = 0;
        boolean failed = false;
        for (Item it : found) {
            if (it.modified < since || now - it.modified < SETTLE_MS) continue;
            String sig = it.sig();
            if (p.recIsDone(sig)) continue;
            try {
                String status = upload(ctx, p, it, sig);
                if ("pending".equals(status)) {
                    if (now - p.recFirstTry(sig, now) > GIVE_UP_MS) {
                        p.recDone(sig, false);
                        p.recError("Mos qo'ng'iroq topilmadi: " + it.name);
                    }
                    continue;
                }
                p.recDone(sig, true);
                sent++;
            } catch (Api.HttpError e) {
                if (e.deviceRevoked()) {
                    p.unpair("Ulanish bekor qilingan — ERP'dan yangi kod olib qayta ulang");
                    return -1;
                }
                if (e.code == 400 || e.code == 413) {  // fayl yaroqsiz yoki juda katta — qayta urinish befoyda
                    p.recDone(sig, false);
                    p.recError(it.name + ": " + e.getMessage());
                } else {
                    p.recError("Server: " + e.getMessage());
                    failed = true;
                    break;
                }
            } catch (IOException e) {
                p.recError("Internet yoki server bilan aloqa yo'q: " + e.getMessage());
                failed = true;
                break;
            }
        }
        if (!failed && sent > 0) p.recError("");
        return failed ? -1 : sent;
    }

    private static String upload(Context ctx, Prefs p, Item it, String sig) throws IOException {
        long durMs = duration(ctx, it.uri);
        JSONObject res;
        try (InputStream in = ctx.getContentResolver().openInputStream(it.uri)) {
            if (in == null) throw new IOException("Faylni ochib bo'lmadi");
            res = Api.upload(p.server(), "recordings/", p.token(), in, it.name,
                    new String[][]{{"ended_at", String.valueOf(it.modified)}, {"duration", String.valueOf(Math.round(durMs / 1000.0))}, {"sig", sig},
                            {"number", numberFromName(it.name)}});
        }
        return res.optString("status");
    }

    private static long duration(Context ctx, Uri uri) {
        MediaMetadataRetriever r = new MediaMetadataRetriever();
        try {
            r.setDataSource(ctx, uri);
            String d = r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION);
            return d == null ? 0 : Long.parseLong(d);
        } catch (RuntimeException e) {
            return 0;
        } finally {
            try {
                r.release();
            } catch (IOException ignored) {
                // yopishdagi xato yuklashga ta'sir qilmaydi
            }
        }
    }

    private static void scan(Context ctx, Uri tree, String parentDocId, int depth, List<Item> out) {
        Uri children = DocumentsContract.buildChildDocumentsUriUsingTree(tree, parentDocId);
        String[] cols = {DocumentsContract.Document.COLUMN_DOCUMENT_ID, DocumentsContract.Document.COLUMN_DISPLAY_NAME,
                DocumentsContract.Document.COLUMN_MIME_TYPE, DocumentsContract.Document.COLUMN_LAST_MODIFIED, DocumentsContract.Document.COLUMN_SIZE};
        List<String> dirs = new ArrayList<>();
        try (Cursor c = ctx.getContentResolver().query(children, cols, null, null, null)) {
            if (c == null) return;
            while (c.moveToNext() && out.size() < MAX_FILES) {
                String id = c.getString(0);
                String name = c.getString(1) == null ? "" : c.getString(1);
                String mime = c.getString(2) == null ? "" : c.getString(2);
                if (DocumentsContract.Document.MIME_TYPE_DIR.equals(mime)) {
                    if (depth < MAX_DEPTH) dirs.add(id);
                    continue;
                }
                if (name.startsWith(".") || !isAudio(name, mime)) continue;
                Item it = new Item();
                it.docId = id;
                it.name = name;
                it.modified = c.getLong(3);
                it.size = c.getLong(4);
                it.uri = DocumentsContract.buildDocumentUriUsingTree(tree, id);
                if (it.size > 0 && it.modified > 0) out.add(it);
            }
        }
        for (String d : dirs) scan(ctx, tree, d, depth + 1, out);
    }

    private static boolean isAudio(String name, String mime) {
        if (mime.startsWith("audio/")) return true;
        String n = name.toLowerCase(Locale.US);
        for (String e : EXT) if (n.endsWith(e)) return true;
        return false;
    }
}
