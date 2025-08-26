# DDNet Map Loader v2 (पोर्टेबल)

यह छोटा टूल आपको किसी भी `.map` फ़ाइल पर डबल‑क्लिक करके उसे आपके लोकल DDNet सर्वर पर हॉट‑रीलोड करने देता है। यह बैकअप और लॉग भी बनाता है।

## 📋 आवश्यकताएँ
- Windows 10/11 (एडमिन की जरूरत नहीं)
- DDNet क्लाइंट/सर्वर इंस्टॉल और लोकल सर्वर उपलब्ध

## 🤔 क्या है और क्यों
- `.map` फाइलों को इस ऐप से एसोसिएट करता है।
- डबल‑क्लिक पर यह:
  - मैप फाइल वेरिफ़ाई करता है
  - वर्तमान मैप का बैकअप बनाता है
  - वर्किंग मैप बदलकर `hot_reload` भेजता है
  - `%APPDATA%\DDNet\maps\ddnet_control.log` में लॉग लिखता है
- तेज़ मैप टेस्टिंग के लिए उपयोगी।

## 🚀 जल्दी कैसे इस्तेमाल करें
1) `myServerconfig.cfg` जाँचें/मूव करें
   - नीचे बताए `data` फोल्डर में कॉपी करें (सिफारिश)।
2) `.map` फाइलों को इस EXE से जोड़ें (अनुशंसित)
   - किसी `.map` पर राइट‑क्लिक → Open with → Choose another app → More apps → Look for another app on this PC
   - इस फ़ोल्डर के `ddnet_control.exe` को चुनें
   - “Always use this app to open .map files” चुनें
   - देखें कि `.map` आइकन बदला या नहीं; नहीं बदला तो नीचे ट्रबलशूटिंग देखें।
   - उन्नत (वैकल्पिक): `registry\setup_map_association_current_user.bat` चला सकते हैं और Explorer रीस्टार्ट करें।
3) किसी भी `.map` पर डबल‑क्लिक
   - उदाहरण: `%APPDATA%\DDNet\maps\mapsfortest\anymap.map`
4) लॉग देखें
   - `%APPDATA%\DDNet\maps\ddnet_control.log`

## 📁 myServerconfig.cfg कहाँ रखें
- DDNet की `data` फोल्डर ढूँढने का आसान तरीका:
  1) टास्कबार/स्टार्ट/डेस्कटॉप पर DDNet शॉर्टकट पर राइट‑क्लिक → Open file location
  2) खुले फोल्डर में `ddnet` (जहाँ `DDNet.exe` है) में जाएँ
  3) `data` सब‑फोल्डर खोलें → `myServerconfig.cfg` कॉपी करें
- आम लोकेशन (उदाहरण):
  - Steam डिफ़ॉल्ट: `C:\Program Files (x86)\Steam\steamapps\common\DDraceNetwork\ddnet\data`
  - अन्य Steam लाइब्रेरी: `<YourSteamLibrary>\steamapps\common\DDraceNetwork\ddnet\data`
  - नॉन‑Steam/पोर्टेबल: `DDNet.exe` के पास वाला `data` फोल्डर

## 🧰 समस्या निवारण
- कंसोल तुरंत बंद हो जाती है
  - आमतौर पर फाइल पाथ पास नहीं हुआ। स्टेप 2 दोहराएँ और Explorer रीस्टार्ट करें।
- “Open with” में ऐप नहीं दिखती
  - “Look for another app on this PC” से `ddnet_control.exe` चुनें और “Always use this app” टिक करें।
- आइकन नहीं बदला
  - Windows Explorer रीस्टार्ट करें (आइकन कैश)।
- हॉट‑रीलोड नहीं हुआ
  - सुनिश्चित करें सर्वर `127.0.0.1:8303` पर चल रहा है और RCON सही है।
  - लॉग में कारण देखें।
- एसोसिएशन हटाएँ
  - चलाएँ: `registry\remove_map_association_current_user.bat`

## 📂 अंदर क्या है
- `ddnet_control.exe`
- `ddnet_loader.ico`
- `myServerconfig.cfg`
- `registry/`
  - `setup_map_association_current_user.bat`
  - `remove_map_association_current_user.bat`