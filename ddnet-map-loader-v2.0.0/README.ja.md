# DDNet Map Loader v2（ポータブル）

`.map` をダブルクリックするだけで、ローカル DDNet サーバーにホットリロードできる小さなツールです。バックアップとログ出力も行います。

## 📋 必要環境
- Windows 10/11（管理者権限不要）
- DDNet クライアント/サーバーが導入され、ローカルサーバーに接続可能

## 🤔 これは何？なぜ必要？
- `.map` ファイルを本アプリに関連付けます。
- ダブルクリック時に：
  - マップを検証
  - 現在のマップをバックアップ
  - 作業用マップに置き換え、`hot_reload` を送信
  - `%APPDATA%\DDNet\maps\ddnet_control.log` にログ
- マップ作成時の素早い動作確認に便利です。

## 🚀 使い方（クイック）
1) `myServerconfig.cfg` を確認/移動
2) `.map` をこの EXE に関連付け（推奨）
   - 任意の `.map` を右クリック → プログラムから開く → 別のアプリを選択 → その他のアプリ → この PC で別のアプリを探す → 本フォルダの `ddnet_control.exe`
   - 「常にこのアプリを使って開く」にチェック
3) 任意の `.map` をダブルクリック（例：`%APPDATA%\DDNet\maps\mapsfortest\anymap.map`）
4) ログ確認：`%APPDATA%\DDNet\maps\ddnet_control.log`

## 📁 myServerconfig.cfg の配置先
- DDNet の `data` フォルダを見つける簡単な方法：
  1) タスクバー/スタート/デスクトップの DDNet ショートカットを右クリック → ファイルの場所を開く
  2) 開いたフォルダで `ddnet`（`DDNet.exe` がある場所）へ
  3) `data` フォルダを開き、`myServerconfig.cfg` をコピー
- 代表例（環境により異なる）：
  - Steam 既定: `C:\Program Files (x86)\Steam\steamapps\common\DDraceNetwork\ddnet\data`
  - 別ライブラリ: `<YourSteamLibrary>\steamapps\common\DDraceNetwork\ddnet\data`
  - 非 Steam/ポータブル: `DDNet.exe` と同じ場所の `data`

## 🧰 トラブルシューティング
- すぐ閉じる → パスが渡されていない可能性。手順2を再実施し、Explorer を再起動。
- 「プログラムから開く」に出ない → 「この PC で別のアプリを探す」で `ddnet_control.exe` を選び、常に使用にチェック。
- アイコンが変わらない → Explorer を再起動（アイコンキャッシュ）。
- hot‑reload しない → `127.0.0.1:8303` でサーバー稼働/RCON 設定確認。ログ参照。
- 解除 → `registry\remove_map_association_current_user.bat`

## 📂 同梱物
- `ddnet_control.exe`
- `ddnet_loader.ico`
- `myServerconfig.cfg`
- `registry/`
  - `setup_map_association_current_user.bat`
  - `remove_map_association_current_user.bat`