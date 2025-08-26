# DDNet Map Loader v2 (পোর্টেবল)

ছোট একটি টুল: যেকোনো `.map` ফাইলে ডাবল‑ক্লিক করলে আপনার লোকাল DDNet সার্ভারে হট‑রিলোড হবে। ব্যাকআপ ও লগও রাখে।

## 📋 প্রয়োজনীয়তা
- Windows 10/11 (অ্যাডমিন দরকার নেই)
- DDNet ক্লায়েন্ট/সার্ভার ইনস্টল ও লোকাল সার্ভার অ্যাক্সেসযোগ্য

## 🤔 কী এবং কেন
- `.map` ফাইলকে এই অ্যাপের সাথে অ্যাসোসিয়েট করে।
- ডাবল‑ক্লিকে:
  - ম্যাপ ফাইল ভেরিফাই করে
  - বর্তমান ম্যাপের ব্যাকআপ নেয়
  - ওয়ার্কিং ম্যাপ বদলে `hot_reload` পাঠায়
  - `%APPDATA%\DDNet\maps\ddnet_control.log` এ লগ লেখে
- দ্রুত টেস্টিংয়ের জন্য ভালো।

## 🚀 কুইক ইউজ
1) `myServerconfig.cfg` চেক/মুভ করুন
2) `.map` এই EXE এর সাথে অ্যাসোসিয়েট করুন (রেকমেন্ডেড)
   - কোনো `.map` ফাইলে রাইট‑ক্লিক → Open with → Choose another app → More apps → Look for another app on this PC → `ddnet_control.exe`
   - “Always use this app…” টিক দিন
3) যে কোনো `.map` ডাবল‑ক্লিক করুন (উদাহরণ: `%APPDATA%\DDNet\maps\mapsfortest\anymap.map`)
4) লগ দেখুন: `%APPDATA%\DDNet\maps\ddnet_control.log`

## 📁 myServerconfig.cfg কোথায় রাখবেন
- DDNet এর `data` ফোল্ডার খুঁজতে সহজ উপায়:
  1) টাস্কবার/స్టার্ট/ডেস্কটপে DDNet শর্টকাটে রাইট‑ক্লিক → Open file location
  2) খোলা ফোল্ডারে `ddnet` (যেখানে `DDNet.exe`) এ যান
  3) `data` ফোল্ডার খুলে `myServerconfig.cfg` কপি করুন
- সাধারণ লোকেশন (উদাহরণ):
  - Steam ডিফল্ট: `C:\Program Files (x86)\Steam\steamapps\common\DDraceNetwork\ddnet\data`
  - অন্য Steam লাইব্রেরি: `<YourSteamLibrary>\steamapps\common\DDraceNetwork\ddnet\data`
  - নন‑Steam/পোর্টেবল: `DDNet.exe` এর পাশের `data`

## 🧰 ট্রাবলশুটিং
- কনসোল দ্রুত বন্ধ হয়ে যায় → সাধারণত পাথ যায়নি; স্টেপ 2 রিপিট করুন, Explorer রিস্টার্ট করুন।
- “Open with” এ না দেখালে → Browse করে `ddnet_control.exe` সিলেক্ট, “Always use…” টিক দিন।
- আইকন বদলায়নি → Windows Explorer রিস্টার্ট (আইকন ক্যাশ)।
- হট‑রিলোড হয়নি → সার্ভার `127.0.0.1:8303`, RCON সঠিক কিনা দেখুন; লগ দেখুন।
- অ্যাসোসিয়েশন অপসারণ → `registry\remove_map_association_current_user.bat`

## 📂 ভিতরে কী আছে
- `ddnet_control.exe`
- `ddnet_loader.ico`
- `myServerconfig.cfg`
- `registry/`
  - `setup_map_association_current_user.bat`
  - `remove_map_association_current_user.bat`