# Codial qo'ng'iroqlar - APK yig'ish (Windows, Android Studio o'rnatilgan kompyuter).
# Natija: android\app\build\outputs\apk\debug\app-debug.apk
# Fayl faqat ASCII: Windows PowerShell 5.1 BOM'siz UTF-8 ni noto'g'ri o'qiydi.
$ErrorActionPreference = "Stop"
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$gradle = Get-ChildItem "$env:USERPROFILE\.gradle\wrapper\dists\gradle-9.*-bin\*\gradle-9.*\bin\gradle.bat" | Select-Object -First 1
if (-not $gradle) { throw "Gradle 9 topilmadi - loyihani bir marta Android Studio'da oching" }
Set-Location $PSScriptRoot
& $gradle.FullName --offline assembleDebug
Get-Item app\build\outputs\apk\debug\app-debug.apk
