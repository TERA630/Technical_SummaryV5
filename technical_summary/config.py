NORMAL_GOOD_DEV25_MIN = -2.0
NORMAL_GOOD_DEV25_MAX = 4.0
STRONG_THEME_GOOD_DEV25_MAX = 8.0
MAIN_GOOD_DEV25_MIN = 1.0
MAIN_GOOD_DEV25_MAX = 7.0
MAIN_HIGH_DEV25_MAX = 12.0
RSI_MAIN_MAX = 65.0
RSI_HIGH_MAX = 70.0
VWAP_NEAR_MIN = -0.5
VWAP_NEAR_MAX = 0.5
VWAP_RECOVERY_MIN = -2.0
DEEP_MA25_BREAK_DEV25 = -3.0
VOLUME_AVG_DAYS = 20
MAX_WORKERS = 6

# 業種データなしでも使えるよう、強テーマはコード・銘柄名で暫定判定する。
# 必要に応じてここへ追加する。
STRONG_THEME_CODES = {
    # 半導体・半導体材料・製造装置・電子部品
    "3436",
    "4063",
    "6315",
    "6323",
    "6503",
    "6754",
    "6954",
    "6963",
    "3132",
    # 電線・電力インフラ
    "5802",
    "5803",
    # 防衛・重工・宇宙関連
    "7011",
    "7721",
    "6946",
    # AI/情報通信・大型ハイテク候補
    "6501",
    "6701",
}

STRONG_THEME_KEYWORDS = [
    "半導体",
    "信越",
    "SUMCO",
    "ローツェ",
    "TOWA",
    "マクニカ",
    "ローム",
    "ファナック",
    "フジクラ",
    "住友電",
    "電線",
    "三菱電機",
    "日立",
    "日本電気",
    "NEC",
    "三菱重工",
    "東京計器",
    "アビオニクス",
    "防衛",
    "重工",
]

CATEGORY_ORDER = [
    "A1.主役押し目",
    "A2.通常位置良好",
    "B1.高値圏",
    "B2.過熱",
    "C.弱い戻り",
    "E.VWAP回復待ち",
    "D.トレンド弱い",
]

