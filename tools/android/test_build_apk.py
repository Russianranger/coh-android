"""Validate real aapt2 badging dialects without relaxing APK identity checks."""
import unittest
from build_apk import APP_ID, VERSION_CODE, VERSION_NAME, verify_badging


class BadgingTests(unittest.TestCase):
    def sample(self, minimum="minSdkVersion:'26'", target="targetSdkVersion:'35'",
               native="native-code: 'arm64-v8a'", app_id=APP_ID,
               version_code=VERSION_CODE, version_name=VERSION_NAME):
        return (f"package: name='{app_id}' versionCode='{version_code}' versionName='{version_name}' "
                "platformBuildVersionName='15' platformBuildVersionCode='35'\n"
                f"{minimum}\n{target}\n{native}\n"
                f"launchable-activity: name='{APP_ID}.MainActivity' label='' icon=''\n")

    def test_sdk35_minimum_label(self):
        verify_badging(self.sample())

    def test_older_sdk_label(self):
        verify_badging(self.sample(minimum="sdkVersion:'26'"))

    def test_missing_or_wrong_minimum_fails(self):
        for value in ("", "minSdkVersion:'25'", "sdkVersion:'27'",
                      "minSdkVersion:'26'\nsdkVersion:'25'"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'SDK mismatch'):
                verify_badging(self.sample(minimum=value))

    def test_missing_or_wrong_target_fails(self):
        for value in ("", "targetSdkVersion:'34'", "targetSdkVersion:'35'\ntargetSdkVersion:'36'"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'SDK mismatch'):
                verify_badging(self.sample(target=value))

    def test_wrong_identity_fails(self):
        with self.assertRaisesRegex(ValueError, 'package/version'):
            verify_badging(self.sample(app_id='com.example.other'))

    def test_previous_apk_version_fails(self):
        for code, name in ((1, '0.1.0'), (1, VERSION_NAME), (VERSION_CODE, '0.1.0')):
            with self.subTest(code=code, name=name), self.assertRaisesRegex(ValueError, 'package/version'):
                verify_badging(self.sample(version_code=code, version_name=name))

    def test_extra_architecture_fails(self):
        with self.assertRaisesRegex(ValueError, 'only ARM64'):
            verify_badging(self.sample(native="native-code: 'arm64-v8a' 'x86_64'"))


if __name__ == '__main__':
    unittest.main()
