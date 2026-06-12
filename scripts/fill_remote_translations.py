#!/usr/bin/env python3
"""Generate a broader English translation CSV for remote Kiou bundles."""

from __future__ import annotations

import csv
import re
from pathlib import Path


JP_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
JP_RANKS = {
    "一": "一",
    "二": "二",
    "三": "三",
    "四": "四",
    "五": "五",
    "六": "六",
    "七": "七",
    "八": "八",
    "九": "九",
}
RANK_CHARS = "".join(JP_RANKS)
PIECES = {
    "歩": "Pawn",
    "香": "Lance",
    "桂": "Knight",
    "銀": "Silver",
    "金": "Gold",
    "角": "Bishop",
    "飛": "Rook",
    "玉": "King",
    "王": "King",
    "と": "Tokin",
}


TRANSLATIONS = {
    "飛車香落ち": "Rook-Lance Handicap",
    "履歴はありません。": "No history.",
    "棋譜履歴": "Game Record History",
    "対局相手名": "Opponent Name",
    "先手": "Sente",
    "プロフィール": "Profile",
    "棋譜": "Game Record",
    "全国対局": "Ranked Match",
    "絞り込み": "Filter",
    "セリフ": "Voice Lines",
    "スキップ": "Skip",
    "詰道場 / 詰将棋": "Tsume Dojo / Tsume Shogi",
    "リセット": "Reset",
    "次の問題へ": "Next Problem",
    "将棋のルール": "Shogi Rules",
    "３手詰": "Mate in 3",
    "3手詰": "Mate in 3",
    "正解時に一時停止": "Pause on Correct Answer",
    "1手戻す": "Undo 1 Move",
    "ルーム設定": "Room Settings",
    "待機中": "Waiting",
    "対局中": "In Match",
    "着席": "Sit",
    "手番: ランダム": "Turn: Random",
    "ルームID: -": "Room ID: -",
    "手番: 先手": "Turn: Sente",
    "手番: 後手": "Turn: Gote",
    "プレイヤー名": "Player Name",
    "観戦": "Spectate",
    "卓3": "Table 3",
    "卓1": "Table 1",
    "卓2": "Table 2",
    "卓4": "Table 4",
    "メンバー": "Members",
    "チャット": "Chat",
    "コピー": "Copy",
    "年齢: 歳": "Age: years",
    "絆レベル１で解放": "Unlocked at Bond Lv. 1",
    "贈り物": "Gifts",
    "師弟契約済！": "Mentorship Active!",
    "CV: 声優名": "VA: Voice Actor",
    "棋士": "Shogi Player",
    "師弟契約": "Mentorship",
    "キャラクター名（ひらがな）": "Character Name (Hiragana)",
    "説明": "Description",
    "親密度: {0} / 5": "Bond: {0} / 5",
    "身長: cm": "Height: cm",
    "ボイス": "Voice",
    "好きな戦法:": "Favorite Strategy:",
    "親密度: 0 / 5": "Bond: 0 / 5",
    "誕生日: 月日": "Birthday: Month/Day",
    "ボイス名": "Voice Name",
    "メンバー一覧": "Member List",
    "詳細": "Details",
    "ルーム主": "Room Host",
    "メンバーはいません。": "No members.",
    "クレジット": "Credits",
    "1手詰": "Mate in 1",
    "棋桜オリジナル問題": "Original Kiou Problems",
    "所持アイテムはありません。": "You have no items.",
    "親密度pt +{0}": "Bond Pt. +{0}",
    "ランク対局": "Ranked Match",
    "戻る": "Back",
    "獲得報酬一覧": "Rewards Earned",
    "なし": "None",
    "絆経験値+0": "Bond EXP +0",
    "投了 24手": "Resignation, 24 moves",
    "初心者サポート": "Beginner Support",
    "ルーム公開設定": "Room Visibility",
    "ルーム主以外は設定を変更できません。": "Only the room host can change settings.",
    "ランダム": "Random",
    "秒読み": "Byoyomi",
    "持ち時間": "Time Limit",
    "棋桜覚醒の使用回数": "Kiou Awakening Uses",
    "手番": "Turn",
    "30秒": "30 sec",
    "ルール": "Rules",
    "10分": "10 min",
    "固定": "Fixed",
    "ルームIDを表示する": "Show Room ID",
    "加算": "Increment",
    "特別な贈り物": "Special Gift",
    "アイテム名": "Item Name",
    "親密度が5になると\n師弟契約を結ぶことができます。": "When Bond reaches 5,\nyou can form a mentorship.",
    "師弟契約済です。": "Mentorship already active.",
    "アイテムはありません。": "No items.",
    "以下の報酬を獲得しました。": "You received the following rewards.",
    "報酬獲得": "Rewards Received",
    "保管庫": "Storage",
    "運営からの個別メッセージはありません。": "No personal messages from the team.",
    "タイトル": "Title",
    "戦績": "Record",
    "マスタリーはありません。": "No mastery entries.",
    "通算勝率": "Overall Win Rate",
    "5分+5秒追加": "5 min + 5 sec increment",
    "3分切れ負け": "3 min sudden death",
    "名前変更": "Change Name",
    "先手勝率": "Sente Win Rate",
    "棋譜一覧": "Game Records",
    "お気に入り": "Favorites",
    "マスタリー": "Mastery",
    "装飾品設定": "Cosmetic Settings",
    "段級": "Rank",
    "違反報告": "Report Violation",
    "囲い": "Castle",
    "戦法": "Strategy",
    "後手勝率": "Gote Win Rate",
    "ユーザー名": "Username",
    "連勝記録": "Win Streak Record",
    "名前": "Name",
    "ギフトはありません。": "No gifts.",
    "あと 999日": "999 days left",
    "受取": "Claim",
    "運営からのプレゼントです。": "A gift from the team.",
    "10回引く": "Draw 10",
    "10回縁結び": "10 Bond Draws",
    "{0}回縁結び": "{0} Bond Draws",
    "あいうえおかきくけこさし": "Sample Player Name",
    "自分のプレイヤー名": "Your Player Name",
    "本譜に戻る": "Return to Main Line",
    "次": "Next",
    "前": "Previous",
    "最初": "First",
    "18級": "18 Kyu",
    "対戦相手のプレイヤー名": "Opponent Player Name",
    "本譜": "Main Line",
    "ここから対局": "Play From Here",
    "最後": "Last",
    "勝利": "Win",
    "プレイヤー": "Player",
    "初段": "1 Dan",
    "後手": "Gote",
    "{0} とアカウントを連携しますか？\n\n<color=#FFC560>{0} に連携できるアカウントは最大1つです。</color>": "Link your account with {0}?\n\n<color=#FFC560>Only one account can be linked to {0}.</color>",
    "{0} とデータを連携しますか？\n\n<color=#FFE223>{0} に連携できるデータは最大1つです。</color>": "Link your data with {0}?\n\n<color=#FFE223>Only one data profile can be linked to {0}.</color>",
    "確認": "Confirm",
    "駒・棋盤などのカスタマイズ": "Customize pieces, boards, and more",
    "所持棋士の詳細": "Owned Player Details",
    "所持アイテムの一覧": "Owned Items",
    "表示物がありません。": "Nothing to display.",
    "表示物はありません。": "Nothing to display.",
    "通常": "Normal",
    "『10回縁結び』をすると紫の贈り物を\n必ず1つ以上獲得できます。": "A 10 Bond Draw guarantees\nat least one Purple Gift.",
    "項目": "Item",
    "提供割合": "Rates",
    "紫の贈り物確定": "Purple Gift Guaranteed",
    "詳細を入力してください（任意）": "Enter details (optional)",
    "不適切なユーザー名": "Inappropriate Username",
    "その他": "Other",
    "このユーザーの違反行為を選んでください。": "Select this user's violation.",
    "ハラスメント行為": "Harassment",
    "不正と思わしき行為": "Suspected Cheating",
    "新着通知があります\n<color=#FF5779>その他</color>": "You have new notifications\n<color=#FF5779>Other</color>",
    "以下のアイテムに変換されました。": "Converted into the following items.",
    "月別勝率": "Monthly Win Rate",
    "残り: 0": "Remaining: 0",
    "テキスト": "Text",
    "逸品": "Rare Item",
    "残り：{0}": "Remaining: {0}",
    "本日残り：{0}": "Today: {0} left",
    "今月残り：{0}": "This month: {0} left",
    "商品": "Product",
    "商品はありません。": "No products.",
    "ルーム参加": "Join Room",
    "ルームIDを入力してください。": "Enter the Room ID.",
    "棋士選択": "Select Player",
    "キャラクター名": "Character Name",
    "棋士詳細": "Player Details",
    "開封": "Open",
    "所持数: 9,999": "Owned: 9,999",
    "アイテム説明文1\nアイテム説明文2\nアイテム説明文3": "Item description 1\nItem description 2\nItem description 3",
    "有効期限: ～0000/00/00 00:00:00": "Expires: until 0000/00/00 00:00:00",
    "装飾品一覧": "Cosmetics List",
    "所持している装飾品はありません。": "You have no cosmetics.",
    "設定中": "Equipped",
    "設定": "Settings",
    "選択": "Select",
    "特別ログインボーナス": "Special Login Bonus",
    "幸運の勾玉ボーナス": "Lucky Magatama Bonus",
    "で1回縁結びしますか？": "Use this for 1 Bond Draw?",
    "棋晶石を使用する場合、無償棋晶石から消費されます。": "When using Kisho Stones, free stones are spent first.",
    "ガチャタイトル": "Gacha Title",
    "で{0}回縁結びしますか？": "Use this for {0} Bond Draws?",
    "結果": "Results",
    "棋士変更": "Change Player",
    "検索": "Search",
    "ユーザーID": "User ID",
    "対局相手を待っています": "Waiting for opponent",
    "準備中...": "Preparing...",
    "準備完了！": "Ready!",
    "交換": "Exchange",
    "価格": "Price",
    "残り": "Remaining",
    "追加購入: ￥ 9,999": "Add Purchase: ¥9,999",
    "有効日数": "Valid Days",
    "未購入": "Not Purchased",
    "残り 999 日": "999 days left",
    "追加購入: ￥{0}": "Add Purchase: ¥{0}",
    "残り{0}日": "{0} days left",
    "ルームを作成して友人同士で対局します。\n段級・レートには影響しません。": "Create a room to play with friends.\nRanks and ratings are unaffected.",
    "あああああいいいいいうう": "Sample Text",
    "セリフ\n": "Voice Lines\n",
    "ラベル": "Label",
    "宝袋開封": "Open Treasure Bag",
    "宝袋を開封しました。": "Opened the Treasure Bag.",
    "対局開始": "Start Match",
    "中級": "Intermediate",
    "アシスト有りで気軽に対戦！\\n 【棋桜覚醒使用可能+無料枠有り / 指し手ガイド有り / 好手判定表示有り】": "Play casually with assists!\\n [Kiou Awakening available + free uses / Move guide / Good move display]",
    "マッチング開始": "Start Matching",
    "上級": "Advanced",
    "ルール選択": "Rule Select",
    "難易度": "Difficulty",
    "無効": "Off",
    "指し手ガイド": "Move Guide",
    "有効": "On",
    "全国のプレイヤーとランダムにマッチングして対局します。\n勝敗によって段級・レートが変動します。": "Match randomly with players nationwide.\nYour rank and rating change based on wins and losses.",
    "選択された条件のCPUと対局します。\n段級・レートには影響しません。": "Play against a CPU with the selected settings.\nRanks and ratings are unaffected.",
    "初級": "Beginner",
    "アシスト無しの真剣勝負！": "A serious match without assists!",
    "一手指すごとに時間回復！\\n【棋桜覚醒使用可能 / 好手判定表示有り】": "Time recovers after each move!\\n[Kiou Awakening available / Good move display]",
    "短い時間で素早く対戦！\\n【棋桜覚醒使用可能 / 好手判定表示有り】": "Fast matches with short time!\\n[Kiou Awakening available / Good move display]",
    "購入可能な商品はありません。": "No products available for purchase.",
    "法令に基づく表記": "Legal Notices",
    "パス": "Pass",
    "手動更新 5/5": "Manual Refresh 5/5",
    "自動更新まで あと 23時間": "Auto refresh in 23 hours",
    "日替わり市": "Daily Market",
    "手動更新 {0}/{1}": "Manual Refresh {0}/{1}",
    "出現: {0}回 / 勝率: {1}": "Used: {0} / Win Rate: {1}",
    "戦法名": "Strategy Name",
    "出現 0回 / 勝率 0.000": "Used 0 / Win Rate 0.000",
    "棋晶石": "Kisho Stones",
    "あと23時間": "23 hours left",
    "商品名": "Product Name",
    "駒名": "Piece Name",
    "成り": "Promotion",
    "詰み": "Mate",
    "持ち駒": "Pieces in Hand",
    "駒の動かし方": "How Pieces Move",
    "将棋の遊び方": "How to Play Shogi",
    "基本": "Basics",
    "注意事項": "Notes",
    "詰道場": "Tsume Dojo",
    "詰将棋": "Tsume Shogi",
    "問題を選択してください。": "Select a problem.",
    "問題選択": "Problem Select",
    "アカウント連携": "Account Linking",
    "メニュー": "Menu",
    "通知一覧": "Notifications",
    "お問い合わせ": "Contact",
    "友人": "Friends",
    "タイトルに戻る": "Return to Title",
    "各種表記": "Legal / Info",
    "運営からのメール": "Messages from Team",
    "お知らせ": "News",
    "運営からのメールはありません。": "No messages from the team.",
    "反転": "Flip",
    "次へ": "Next",
    "継ぎ盤": "Analysis Board",
    "通知はありません。": "No notifications.",
    "メンバー詳細": "Member Details",
    "キック": "Kick",
    "ルーム主を譲渡": "Transfer Host",
    "0回": "0 times",
    "ユーザー名:": "Username:",
    "ユーザー名\n": "Username\n",
    "対局中BGM": "Match BGM",
    "アイテムがありません。": "No items.",
    "変更": "Change",
    "アイコンフレーム": "Icon Frame",
    "アイコン": "Icon",
    "将棋駒": "Shogi Pieces",
    "種別": "Type",
    "称号": "Title",
    "将棋盤": "Shogi Board",
    "並び替え": "Sort",
    "猫宮 さくら": "Sakura Nekomiya",
    "駒落ち": "Handicap",
    "対局相手": "Opponent",
    "あなたの設定": "Your Settings",
    "対局準備": "Match Prep",
    "相手の設定": "Opponent Settings",
    "現在のアカウントを以下のサービスと\n連携することができます。": "You can link the current account\nwith the following services.",
    "個数を選択してください。": "Select a quantity.",
    "個数選択": "Quantity Select",
    "1回縁結び": "1 Bond Draw",
    "棋士名": "Player Name",
    "御守交換": "Charm Exchange",
    "『10回縁結び』をすると<color=#FFC560>紫の贈り物</color>を必ず1つ以上獲得できます": "A 10 Bond Draw guarantees at least one <color=#FFC560>Purple Gift</color>.",
    "贈り物・宝珠の交換": "Gift / Jewel Exchange",
    "パスの購入": "Buy Pass",
    "累計購入額特典": "Total Purchase Bonus",
    "お得なセット販売": "Value Sets",
    "想いの石で交換": "Exchange with Memory Stones",
    "棋晶石を金貨に交換": "Exchange Kisho Stones for Coins",
    "縁結び券・福袋": "Bond Tickets / Lucky Bags",
    "装飾品の石で交換": "Exchange with Cosmetic Stones",
    "棋晶石の購入": "Buy Kisho Stones",
    "利用規約": "Terms of Service",
    "プライバシーポリシー": "Privacy Policy",
    "コピーライト": "Copyright",
    "ガイドライン": "Guidelines",
    "親密度は最大です。": "Bond is at maximum.",
    "贈り物はありません。": "No gifts.",
    "贈る（あと2回）": "Give (2 left)",
    "<size=32>次善</size> 6四歩": "<size=32>Second Best</size> 6四 Pawn",
    "次 ▶": "Next ▶",
    "後手優勢": "Gote Advantage",
    "◀ 前": "◀ Previous",
    "<size=32>最善</size> <size=48>6四歩</size>": "<size=32>Best</size> <size=48>6四 Pawn</size>",
    "勝率 38% (-200)": "Win Rate 38% (-200)",
    "先手優勢": "Sente Advantage",
    "棋譜コピー": "Copy Record",
    "解析": "Analysis",
    "棋譜詳細": "Record Details",
    "想いの市": "Memory Market",
    "{0}回 / 日": "{0} times / day",
    "{0}件": "{0} items",
    "{0}回": "{0} times",
    "棋譜ブックマーク数上限": "Game Record Bookmark Limit",
    "日替わり市 無料更新回数": "Daily Market Free Refreshes",
    "贈り物回数上限": "Gift Limit",
    "奉納レベル": "Offering Level",
    "日替わり市 最大更新回数": "Daily Market Max Refreshes",
    "Lv. 0 の御利益": "Lv. 0 Blessing",
    "Lv.{0} の御利益": "Lv.{0} Blessing",
    "0回 / 日": "0 times / day",
    "報酬: なし": "Reward: None",
    "ランク対局 親密度ボーナス": "Ranked Match Bond Bonus",
    "0件": "0 items",
    "チャット入力": "Chat Input",
    "御守は縁結び1回につき1つ獲得できます。": "You receive one Charm for each Bond Draw.",
    "対局": "Match",
    "ここから対局を始められます。\n全国の強豪と腕を競い合いましょう。": "Start matches here.\nTest your skill against strong players nationwide.",
    "宿舎": "Dorm",
    "宿舎では棋士との親密度を上げたり、\n装飾品をカスタマイズできます。": "In the Dorm, raise bonds with players\nand customize cosmetics.",
    "将棋の遊び方は『メニュー』から\nいつでも見直すことができます。": "You can review how to play Shogi\nfrom the Menu at any time.",
    "縁結び": "Bond Draw",
    "新しい棋士との出会いはこちら。\nお気に入りの一人をお迎えしましょう。": "Meet new shogi players here.\nWelcome your favorite one.",
    "将棋の遊び方について学びますか？": "Learn how to play Shogi?",
    "学ぶ": "Learn",
    "もう一度詰道場に挑戦したい場合はこちら。": "Come here to challenge Tsume Dojo again.",
    "対局の前に詰道場でトレーニングしてみましょう！\n\n（詰道場とは相手の王将を詰ますパズルです）": "Train in Tsume Dojo before a match!\n\n(Tsume Dojo is a puzzle where you checkmate the opponent's king.)",
    "遊ぶ": "Play",
    "ほかにも様々な機能があります。\nぜひ試してみてください。": "There are many other features too.\nTry them out.",
    "市場": "Market",
    "アイテムや装飾品の購入はこちら。\n対局を華やかに彩りましょう。": "Buy items and cosmetics here.\nAdd style to your matches.",
    "棋桜へようこそ": "Welcome to Kiou",
    "簡単にホーム画面の使い方を\nご説明いたします。": "Here is a quick guide\nto the Home screen.",
    "詰道場や詰将棋に挑戦したい場合はこちら。": "Come here to try Tsume Dojo or Tsume Shogi.",
    "{0}勝 {1}敗": "{0}W {1}L",
    "0勝 0敗": "0W 0L",
    "残り2回": "2 left",
    "棋桜覚醒": "Kiou Awakening",
    "覚醒状態に入り、盤上の真理を視る秘術。": "A secret art that awakens you to see the truth of the board.",
    "対局相手を探しています...（0秒）": "Searching for opponent... (0 sec)",
    "お得セット": "Value Set",
    "（本日の無料更新回数: 残り {0}回）": "(Free refreshes today: {0} left)",
    "（本日の無料更新回数: 残り 0回）": "(Free refreshes today: 0 left)",
    "日替わり市の商品を更新しますか？": "Refresh Daily Market products?",
    "本日の無料更新回数を使い切りました。": "You have used all free refreshes today.",
    "無料で更新可能です。": "You can refresh for free.",
    "金貨交換": "Coin Exchange",
    "歩（ふ）": "Pawn",
    "香車（きょうしゃ）": "Lance",
    "桂馬（けいま）": "Knight",
    "銀将（ぎんしょう）": "Silver General",
    "角行（かく）": "Bishop",
    "飛車（ひしゃ）": "Rook",
    "金将（きんしょう）": "Gold General",
    "王将（玉将）": "King",
    "と金（ときん）": "Tokin",
    "成香（なりきょう）": "Promoted Lance",
    "成桂（なりけい）": "Promoted Knight",
    "成銀（なりぎん）": "Promoted Silver",
    "龍馬（りゅうま）": "Horse",
    "龍王（りゅうおう）": "Dragon",
    "彩の市": "Color Market",
    "未受取\n": "Unclaimed\n",
    "受取済のギフトはありません。": "No claimed gifts.",
    "直近30日間で受け取ったギフトが表示されます。": "Gifts claimed in the last 30 days are shown.",
    "一括受取": "Claim All",
    "ギフト": "Gifts",
    "受け取り可能なギフトはありません。": "No gifts available to claim.",
    "受取履歴": "Claim History",
    "商店へ": "To Shop",
    "名前変更券を使用します。": "Use a Name Change Ticket.",
    "一覧": "List",
    "「5秒で解きたい3手詰／小田切秀人／マイナビ出版」": '"Mate in 3 to Solve in 5 Seconds" / Hideto Odagiri / Mynavi Publishing',
}

LONG_TRANSLATIONS = {
    "「詰将棋（つめしょうぎ）」とは、将棋のルールを使った「王手」のパズルゲームです。\nあらかじめ決められた盤面からスタートし、相手の玉を絶対に逃げられない状態（詰み）にすればクリアとなります。\nクリアまでの正解の手順が必ず1つに決まっているのが特徴です.": "",
}

TRANSLATIONS.update(
    {
        "「詰将棋（つめしょうぎ）」とは、将棋のルールを使った「王手」のパズルゲームです。\nあらかじめ決められた盤面からスタートし、相手の玉を絶対に逃げられない状態（詰み）にすればクリアとなります。\nクリアまでの正解の手順が必ず1つに決まっているのが特徴です。": "Tsume Shogi is a checkmate puzzle based on the rules of Shogi.\nYou start from a preset position and clear it by forcing the opponent's king into a position where it cannot escape: checkmate.\nEach problem has exactly one correct sequence to clear it.",
        "■ルール\n・ずっと王手：攻め方は、必ず毎手「王手」をかけ続けなければなりません。\n・最短で詰ます：攻め方は、一番少ない手数で玉を捕まえるのが正解です。\n・全力で逃げる：守り側（玉）は、一番長生きできる最善の方法で逃げます。\n\n■注意点\n・打ち歩詰めの禁止：持ち駒の「歩」を打って、王手をかけてはいけません（盤上の歩を動かして詰ますのはOK）。\n・持ち駒は残さない：玉を詰ませたとき、自分の「持ち駒」が余ってはいけません（綺麗に使い切る）。\n・無駄な合駒はなし：取られるだけの意味のない防御（合駒）は、手数に数えません。": "Rules\n- Continuous checks: the attacker must give check on every move.\n- Shortest mate: the correct line mates the king in the fewest moves.\n- Best defense: the defending king chooses the line that survives longest.\n\nNotes\n- No pawn-drop mate: you may not drop a pawn to give immediate mate. Moving a pawn already on the board to mate is allowed.\n- Use all pieces in hand: when checkmating, you must not have unused pieces in hand.\n- No meaningless interpositions: defensive drops that only get captured and do not affect the mate are not counted.",
        "・それぞれの提供割合の合計値は100%ちょうどにならない場合があります。\n・『10回縁結び』について、10回目は紫の贈り物が確定で登場します。提供割合は「紫の贈り物確定」に従います。": "- Listed rates may not add up to exactly 100%.\n- In a 10 Bond Draw, the 10th draw guarantees a Purple Gift. Its rates follow the Purple Gift Guaranteed table.",
        "・縁結び1回につき御守を1つ獲得することができます。獲得した御守は棋士や装飾品などと交換することができます。\n・『通常縁結び』では【紅の御守】を獲得することができます。\n・『イベント縁結び』では【金の御守】を獲得することができます。": "- You receive one Charm for each Bond Draw. Charms can be exchanged for shogi players, cosmetics, and more.\n- Normal Bond Draws give Crimson Charms.\n- Event Bond Draws give Gold Charms.",
        "「詰道場（つめどうじょう）」とは、将棋のルールを使った「王手」のパズルゲームです。\nあらかじめ決められた盤面からスタートし、相手の玉を絶対に逃げられない状態（詰み）にすればクリアとなります。": "Tsume Dojo is a checkmate puzzle based on the rules of Shogi.\nYou start from a preset position and clear it by forcing the opponent's king into checkmate.",
        "■ルール\n・ずっと王手：攻め方は、必ず毎手「王手」をかけ続けなければなりません。\n・全力で逃げる：守り側（玉）は、一番長生きできる最善の方法で逃げます。\n\n■注意点\n・打ち歩詰めの禁止：持ち駒の「歩」を打って、王手をかけてはいけません（盤上の歩を動かして詰ますのはOK）。": "Rules\n- Continuous checks: the attacker must give check on every move.\n- Best defense: the defending king chooses the line that survives longest.\n\nNotes\n- No pawn-drop mate: you may not drop a pawn to give immediate mate. Moving a pawn already on the board to mate is allowed.",
        "・各縁結びの開催期間および内容は予告なく変更する場合があります。\n・『イベント縁結び』で登場する棋士や装飾品は、後日再登場する場合があります。\n・すでに獲得済の棋士は【想いの石】に変換されます。\n・すでに獲得済の装飾品は【装飾品の石】に変換されます。": "- Bond Draw periods and contents may change without notice.\n- Shogi players and cosmetics from Event Bond Draws may return later.\n- Duplicate shogi players are converted into Memory Stones.\n- Duplicate cosmetics are converted into Cosmetic Stones.",
        "前に1マスだけ進むことができます。\n最も弱い駒ですが、陣形の土台や攻めの起点などさまざまな場面で活躍します。": "Moves one square forward.\nIt is the weakest piece, but it plays many roles: building formations, starting attacks, and more.",
        "前方にどこまでも突き進むことができます。直線上の破壊力は高いものの横や後ろには一切動けないため、打ちこむ際には注意が必要です。": "Moves any number of squares straight forward. It is powerful on open files, but cannot move sideways or backward, so drops require care.",
        "前方に2マス、そこから左右に1マスの地点へ跳ぶ、将棋で唯一ほかの駒を飛び越えられる駒です。前にしか跳べず後退できないため、タイミングを見極めることが重要です。": "Jumps two squares forward and one square left or right. It is the only shogi piece that can jump over other pieces. Since it only jumps forward and cannot retreat, timing is vital.",
        "前方3方向と斜め後ろ2方向に進むことができます。前線で動き回り相手の守りをこじ開ける攻めの使い方が特に光ります。": "Moves to the three forward-adjacent squares and the two backward diagonals. It shines as an attacking piece that opens up the opponent's defense.",
        "斜め方向に直進できる大駒です。離れた場所からの破壊力がありますが、縦横には動けず死角も多いため序盤は自陣からにらみを利かせつつ、切り込むタイミングを見極めるのがポイントです。": "A major piece that moves any distance diagonally. It has long-range power, but cannot move orthogonally and has blind spots, so watch for the right time to break through.",
        "縦横にどこまでも進められる、将棋で最も攻撃力の高い駒です。まずは飛車をうまく活用して成らせることを目標にしましょう。": "Moves any distance vertically or horizontally, making it shogi's strongest attacking piece. Use it well and aim to promote it.",
        "前方への利きが広く、守りの要となる駒です。玉の囲いを固めるのに最適で、終盤では相手玉の真上に打つ「頭金」が強力な詰み筋になります。成ることはできません。": "A key defensive piece with strong forward coverage. It is ideal for castles, and in the endgame a Gold dropped directly above the king is a powerful mating pattern. It cannot promote.",
        "全方向に1マスずつ進める、最も重要な駒です。この駒を取られると負けになるため、囲いの中でしっかり守りましょう。終盤では相手の攻め駒から逃げきる判断力が勝敗を分けます。": "The most important piece, moving one square in any direction. If it is captured, you lose, so protect it inside a castle. In the endgame, escaping attacks decides the match.",
        "金将と同じ動きになり、相手にとられても大きな痛手にはなりにくく、厳しい攻めを展開することができます。": "Moves like a Gold General. Even if captured, it is usually not a major loss, making it excellent for strong attacks.",
        "金将と同じ動きになり、前にしか進めない制約がなくなります。敵陣に突き進んだ後は成ることで、そのまま柔軟な攻め駒として立ち回ることができます。": "Moves like a Gold General, removing the Lance's forward-only limit. After entering enemy territory, promote it into a flexible attacking piece.",
        "金将と同じ動きになり、跳ぶ力は失われますが全方向にバランスよく動けるようになります。敵陣に跳ね込んだ後は成って安定した攻め駒として活用しましょう。": "Moves like a Gold General. It loses the Knight's jump, but gains balanced movement. After jumping into enemy territory, promote it for stable attacking power.",
        "真横と真後ろに動けない弱点が解消されますが、斜め後ろへの利きは失われるため、局面によってはあえて成らず銀のまま使う判断も大切です。": "Promotion fixes its inability to move sideways or straight back, but it loses backward-diagonal moves. Depending on the position, keeping it as a Silver can be best.",
        "角の動きに縦横1マスが加わり、弱点だった死角が解消された万能駒です。攻めに使うだけでなく、自玉の近くに引きつけて守りの要として使うのも非常に強力です。": "A promoted Bishop that also moves one square orthogonally. Its blind spots are covered, making it a versatile piece for both attack and defense.",
        "飛車の動きに加え、斜めにも1マス進めるようになった最強の駒です。敵陣に成り込んだら相手玉の逃げ道を制限しつつ、一気に勝負を決めにいきましょう。": "A promoted Rook that also moves one square diagonally. It is the strongest piece; use it to restrict the king's escape and finish the game.",
    }
)


def translate_move_token(token: str) -> str:
    token = token.translate(JP_DIGITS)
    token = token.replace("同", "same ")
    for jp, en in JP_RANKS.items():
        token = token.replace(jp, en)
    token = token.replace("成", "+")
    token = token.replace("打", " drop")
    for jp, en in PIECES.items():
        token = token.replace(jp, en)
    token = re.sub(rf"([1-9][{RANK_CHARS}])([A-Z])", r"\1 \2", token)
    return token


def translate_notation(source: str) -> str | None:
    m = re.fullmatch(r"(\d+)手目: ([▲△])(.+)", source.translate(JP_DIGITS))
    if m:
        return f"Move {m.group(1)}: {m.group(2)}{translate_move_token(m.group(3))}"

    m = re.fullmatch(r"([▲△])(.+)", source.translate(JP_DIGITS))
    if m:
        return f"{m.group(1)}{translate_move_token(m.group(2))}"

    m = re.fullmatch(r"(\d+) (先手|後手) ([▲△].+)", source.translate(JP_DIGITS))
    if m:
        side = "Sente" if m.group(2) == "先手" else "Gote"
        return f"{m.group(1)} {side} {translate_move_token(m.group(3))}"

    m = re.fullmatch(r"(\d+)手\n?", source.translate(JP_DIGITS))
    if m:
        suffix = "\n" if source.endswith("\n") else ""
        return f"{m.group(1)} moves{suffix}"

    m = re.fullmatch(r"(\d+)分[＋+](\d+)秒(?:追加)?", source.translate(JP_DIGITS))
    if m:
        return f"{m.group(1)} min + {m.group(2)} sec"

    m = re.fullmatch(r"(\d+)分(\d+)秒", source.translate(JP_DIGITS))
    if m:
        return f"{m.group(1)} min {m.group(2)} sec"

    m = re.fullmatch(r"(\d+) / (\d+)手", source.translate(JP_DIGITS))
    if m:
        return f"{m.group(1)} / {m.group(2)} moves"

    m = re.fullmatch(r"(\d+)<size=24>手目</size>", source.translate(JP_DIGITS))
    if m:
        return f"<size=24>Move</size> {m.group(1)}"

    m = re.fullmatch(r"\{0\} \{1\}手", source)
    if m:
        return "{0} {1} moves"

    m = re.fullmatch(r"\{0\}手", source)
    if m:
        return "{0} moves"

    return None


def translate(source: str) -> str:
    if source in TRANSLATIONS:
        return TRANSLATIONS[source]
    notation = translate_notation(source)
    if notation:
        return notation
    return ""


def main() -> int:
    template = Path("translations/remote_ui_template.csv")
    output = Path("translations/remote_ui.csv")
    rows = list(csv.DictReader(template.open(encoding="utf-8")))
    missing = []
    for row in rows:
        target = translate(row["source"])
        if not target:
            missing.append(row["source"])
        row["target"] = target

    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "target"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {output}")
    print(f"Translated {len(rows) - len(missing)} / {len(rows)}")
    if missing:
        print("Missing:")
        for item in missing:
            print(repr(item))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
