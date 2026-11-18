plugins {
    id("com.android.application")
}

android {
    namespace = "uz.codial.calls"
    compileSdk = 36

    defaultConfig {
        applicationId = "uz.codial.calls"
        minSdk = 26
        targetSdk = 36
        versionCode = 6
        versionName = "1.4.1"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
