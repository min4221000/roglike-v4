# assets.py
import copy
import random

# ── 스테이지 정보 (AI 페르소나 포함) ──
STAGE_INFO = {
    1: {"name": "초보자의 숲",   "multiplier": 1.0, "persona": "인간의 말을 배운 숲의 오래된 정령, 고풍스럽고 약간 조롱하는 말투"},
    2: {"name": "어둠의 던전",   "multiplier": 1.5, "persona": "사람의 언어를 구사하는 지하 감시자, 냉정하고 위협적인 짐승 같은 존재"},
}

def get_stage_by_floor(floor):
    if floor <= 15: return 1
    return 2

# ── 상태이상 정보 ──
STATUS_INFO = {
    "burn":       {"name": "화상",      "desc": "매 턴 5 고정 피해. 지속 턴마다 1 감소."},
    "poison":     {"name": "중독",      "desc": "매 턴 스택만큼 피해 후 스택 1 감소. 스택 0이면 해제."},
    "stun":       {"name": "기절",      "desc": "해당 턴 행동 불가."},
    "vulnerable": {"name": "취약",      "desc": "받는 피해 50% 증가."},
    "weak":       {"name": "약화",      "desc": "주는 피해 25% 감소."},
    "atk_up":     {"name": "공격 강화", "desc": "공격력 20% 상승. 지속 턴마다 1 감소."},
    "def_up":     {"name": "방어막",    "desc": "받는 피해 30% 감소. 지속 턴마다 1 감소."},
}

# ── 1. 직업 데이터 ──
CLASSES = {
    "전사": {
        "name": "전사", "hp": 90, "mp": 3, "atk": 12, "spd": 10,
        "type": "melee",
        "deck": ["강타", "강타", "강타", "방패막기", "방패막기", "도발", "응급처치"]
    },
    "마법사": {
        "name": "마법사", "hp": 50, "mp": 4, "atk": 14, "spd": 12,
        "type": "ranged",
        "deck": ["화염구", "화염구", "화염구", "독구름", "마법방어막", "번개화살", "저주의손길", "치유의빛"]
    }
}

# ── 2. 카드 데이터 (형식: "한줄 요약 / 수치") ──
CARDS = {
    # 전사 전용
    "강타":       {"name": "강타",       "class": "전사",  "cost": 1, "damage_mult": 1.5, "heal": 0,  "target": "enemy",    "effect": None,        "description": "힘껏 내려칩니다 / 공격력 × 1.5 피해"},
    "방패막기":   {"name": "방패막기",   "class": "전사",  "cost": 1, "damage_mult": 0,   "heal": 0,  "target": "self",     "effect": "def_up",    "description": "방어 자세를 취합니다 / 3턴간 받는 피해 30% 감소"},
    "연속베기":   {"name": "연속베기",   "class": "전사",  "cost": 2, "damage_mult": 2.2, "heal": 0,  "target": "enemy",    "effect": None,        "description": "빠르게 두 번 베어냅니다 / 공격력 × 2.2 피해"},
    "압박":       {"name": "압박",       "class": "전사",  "cost": 2, "damage_mult": 0.8, "heal": 0,  "target": "enemy",    "effect": "vulnerable","description": "적의 빈틈을 파고듭니다 / 공격력 × 0.8 피해 + 취약 2턴"},
    "도발":       {"name": "도발",       "class": "전사",  "cost": 1, "damage_mult": 0,   "heal": 0,  "target": "enemy",    "effect": "weak",      "description": "집중력을 흐뜨립니다 / 적에게 약화 2턴 (공격력 25% 감소)"},
    "전투의함성": {"name": "전투의함성", "class": "전사",  "cost": 2, "damage_mult": 0,   "heal": 0,  "target": "party",    "effect": "atk_up",    "description": "파티 사기를 끌어올립니다 / 파티 전체 공격력 20% 상승 (3턴)"},
    "응급처치":   {"name": "응급처치",   "class": "전사",  "cost": 2, "damage_mult": 0,   "heal": 25, "target": "ally",     "effect": None,        "description": "상처를 응급으로 처치합니다 / 아군 1명 HP +25 회복"},
    # 마법사 전용
    "화염구":     {"name": "화염구",     "class": "마법사","cost": 1, "damage_mult": 1.8, "heal": 0,  "target": "enemy",    "effect": "burn",      "description": "불덩어리를 날립니다 / 공격력 × 1.8 피해 + 화상 3턴"},
    "번개화살":   {"name": "번개화살",   "class": "마법사","cost": 2, "damage_mult": 1.5, "heal": 0,  "target": "enemy",    "effect": "stun",      "description": "번개를 압축해 발사합니다 / 공격력 × 1.5 피해 + 기절 1턴 (50% 확률)"},
    "마나폭발":   {"name": "마나폭발",   "class": "마법사","cost": 3, "damage_mult": 2.5, "heal": 0,  "target": "enemy_all","effect": None,        "description": "마력을 한꺼번에 폭발시킵니다 / 공격력 × 2.5 광역 피해 (보상으로만 획득)"},
    "마법방어막": {"name": "마법방어막", "class": "마법사","cost": 1, "damage_mult": 0,   "heal": 0,  "target": "self",     "effect": "def_up",    "description": "마법 장벽을 펼칩니다 / 3턴간 받는 피해 30% 감소"},
    "독구름":     {"name": "독구름",     "class": "마법사","cost": 2, "damage_mult": 0,   "heal": 0,  "target": "enemy",    "effect": "poison",    "description": "독성 안개를 뿜어냅니다 / 적에게 중독 3스택"},
    "저주의손길": {"name": "저주의손길", "class": "마법사","cost": 2, "damage_mult": 0.5, "heal": 0,  "target": "enemy",    "effect": "vulnerable","description": "저주로 방어를 무너뜨립니다 / 공격력 × 0.5 피해 + 취약 2턴"},
    "치유의빛":   {"name": "치유의빛",   "class": "마법사","cost": 2, "damage_mult": 0,   "heal": 40, "target": "ally",     "effect": None,        "description": "빛의 마법으로 상처를 치유합니다 / 아군 1명 HP +40 회복"},
    # 공용 카드
    "마나 회복":  {"name": "마나 회복",  "class": "공용",  "cost": 0, "damage_mult": 0,   "heal": 0,  "target": "self",     "effect": "mp_restore", "description": "에너지를 충전합니다 / 에너지 2~3 즉시 회복"},
    "긴급 교대":  {"name": "긴급 교대",  "class": "공용",  "cost": 0, "damage_mult": 0,   "heal": 0,  "target": "self",     "effect": "swap_free",  "description": "전열을 즉시 교체합니다 / 교대 횟수 소비 없이 스왑"},
    "집중":       {"name": "집중",       "class": "공용",  "cost": 0, "damage_mult": 0,   "heal": 0,  "target": "self",     "effect": "draw2",      "description": "정신을 집중합니다 / 카드 2장 즉시 추가 드로우"},
    "해독제":     {"name": "해독제",     "class": "공용",  "cost": 0, "damage_mult": 0,   "heal": 0,  "target": "ally",     "effect": "cleanse",    "description": "상태이상을 해제합니다 / 아군 1명의 부정적 상태이상 1개 제거"},
}

# ── 3. 몬스터 데이터 ──
MONSTERS = {
    # ── 1스테이지 (기존) ──
    "고블린": {
        "name": "고블린", "stage": 1,
        "base_hp": 40, "base_atk": 8, "base_spd": 5,
        "pattern": ["normal", "power"],
        "reward_gold": 15,
        "speech": "킬킬, 이 던전은 내 구역이야!"
    },
    "늑대": {
        "name": "늑대", "stage": 1,
        "base_hp": 50, "base_atk": 11, "base_spd": 18,
        "pattern": ["normal", "quick", "normal"],
        "reward_gold": 20,
        "speech": "그르르... 내 영역에 들어온 것을 후회하게 해주마."
    },
    # ── 1스테이지 (신규) ──
    "독거미": {
        "name": "독거미", "stage": 1,
        "base_hp": 35, "base_atk": 7, "base_spd": 8,
        "pattern": ["poison_bite", "normal", "poison_bite"],
        "reward_gold": 18,
        "speech": "쉭쉭... 내 독은 천천히 퍼지지. 아주 천천히."
    },
    "오크광전사": {
        "name": "오크 광전사", "stage": 1,
        "base_hp": 60, "base_atk": 13, "base_spd": 4,
        "pattern": ["power", "power", "normal", "power"],
        "reward_gold": 22,
        "speech": "으아아악! 부숴버린다! 다 박살내버려!"
    },
    "도적": {
        "name": "도적", "stage": 1,
        "base_hp": 40, "base_atk": 9, "base_spd": 17,
        "pattern": ["quick", "weaken_slash", "normal"],
        "reward_gold": 20,
        "speech": "쳇, 운이 없군. 죽지 않으려면 지갑이나 내놔."
    },
    # ── 2스테이지 (기존, 공격력 하향) ──
    "해골전사": {
        "name": "해골전사", "stage": 2,
        "base_hp": 90, "base_atk": 12, "base_spd": 7,
        "pattern": ["normal", "quick", "power"],
        "reward_gold": 30,
        "speech": "나는... 죽지 않아. 다시... 일어선다."
    },
    "불도마뱀": {
        "name": "불도마뱀", "stage": 2,
        "base_hp": 75, "base_atk": 14, "base_spd": 14,
        "pattern": ["normal", "fire_aoe"],
        "reward_gold": 35,
        "speech": "이 열기는 맛보기야. 진짜 불꽃은 이제부터지."
    },
    # ── 2스테이지 (신규) ──
    "저주기사": {
        "name": "저주받은 기사", "stage": 2,
        "base_hp": 90, "base_atk": 13, "base_spd": 6,
        "pattern": ["vulnerable_strike", "power", "normal"],
        "reward_gold": 40,
        "speech": "이 저주는 너희도 받아야 해. 나처럼... 영원히."
    },
    "독마녀": {
        "name": "독 마녀", "stage": 2,
        "base_hp": 75, "base_atk": 11, "base_spd": 11,
        "pattern": ["poison_aoe", "normal", "normal", "poison_aoe"],
        "reward_gold": 45,
        "speech": "내 비약을 맛봐라. 고통은... 아름다운 것이니까."
    },
    "광분전사": {
        "name": "광분한 전사", "stage": 2,
        "base_hp": 110, "base_atk": 15, "base_spd": 9,
        "pattern": ["power", "quick", "power", "aoe"],
        "reward_gold": 50,
        "speech": "더 강해져라! 더! 그래야 죽여줄 맛이 나지!"
    },
}

BOSSES = {
    15: {
        "name": "숲의 군주", "base_hp": 300, "base_atk": 25, "base_spd": 10,
        "pattern": ["normal", "power", "quick"],
        "reward_gold": 100,
        "speech": "하찮은 인간들아. 이 숲은 내가 지배한다. 영원히."
    },
    30: {
        "name": "심연의 근원", "base_hp": 430, "base_atk": 23, "base_spd": 22,
        "pattern": ["quick", "dark_slash", "aoe"],
        "reward_gold": 500,
        "speech": "너희의 여정은 여기서 끝난다. 심연은 모든 것을 삼킨다."
    },
}

# ── 4. 유물 데이터 (형식: "효과 설명") ──
RELICS = {
    # 기존 스테이지 1
    "낡은나침반":  {"name": "낡은 나침반",  "stage": 1, "price": 40,  "effect": {"spd": 2},            "desc": "SPD +2"},
    "약초주머니":  {"name": "약초 주머니",  "stage": 1, "price": 50,  "effect": {"hp": 15},            "desc": "최대 HP +15"},
    "숫돌":        {"name": "숫돌",         "stage": 1, "price": 60,  "effect": {"atk": 2},            "desc": "ATK +2"},
    "가죽망토":    {"name": "가죽 망토",    "stage": 1, "price": 55,  "effect": {"hp": 15},            "desc": "최대 HP +15"},
    "나무방패":    {"name": "나무 방패",    "stage": 1, "price": 65,  "effect": {"hp": 20},            "desc": "최대 HP +20"},
    "연습용목검":  {"name": "연습용 목검",  "stage": 1, "price": 70,  "effect": {"atk": 3},            "desc": "ATK +3"},
    "낡은장화":    {"name": "낡은 장화",    "stage": 1, "price": 45,  "effect": {"spd": 3},            "desc": "SPD +3"},
    "독침":        {"name": "독침",         "stage": 1, "price": 60,  "effect": {"poison_start": 1},   "desc": "전투 시작 시 적에게 중독 1스택"},
    "행운의동전":  {"name": "행운의 동전",  "stage": 1, "price": 50,  "effect": {"atk": 1, "spd": 1}, "desc": "ATK +1, SPD +1"},
    "마력결정":    {"name": "마력 결정",    "stage": 1, "price": 60,  "effect": {"bonus_energy": 1},   "desc": "매 턴 시작 시 에너지 +1"},
    # 신규 스테이지 1 (쌍)
    "화염징표":    {"name": "화염의 징표",  "stage": 1, "price": 65,  "effect": {"burn_start": 2},     "desc": "전투 시작 시 적에게 화상 2턴"},
    "분노인장":    {"name": "분노의 인장",  "stage": 1, "price": 70,  "effect": {"atk": 2, "hp_drain": 3}, "desc": "ATK +2 / 매 전투 턴 HP -3"},
    # 기존 스테이지 2
    "기사의휘장":  {"name": "기사의 휘장",  "stage": 2, "price": 100, "effect": {"atk": 5},            "desc": "ATK +5"},
    "강철갑옷":    {"name": "강철 갑옷",    "stage": 2, "price": 110, "effect": {"hp": 30},            "desc": "최대 HP +30"},
    "마도사의반지":{"name": "마도사의 반지","stage": 2, "price": 150, "effect": {"bonus_energy": 1},   "desc": "매 턴 시작 시 에너지 +1"},
    "거인의심장":  {"name": "거인의 심장",  "stage": 2, "price": 150, "effect": {"hp": 40},            "desc": "최대 HP +40"},
    "강독침":      {"name": "강독침",       "stage": 2, "price": 65,  "effect": {"poison_start": 2},   "desc": "전투 시작 시 적에게 중독 2스택"},
    "피의서약":    {"name": "피의 서약",    "stage": 2, "price": 70,  "effect": {"atk": 3, "hp_drain": 4}, "desc": "ATK +3 / 매 전투 턴 HP -4"},
    "약화부적":    {"name": "약화의 부적",  "stage": 2, "price": 75,  "effect": {"duration_bonus": 1}, "desc": "약화·취약·화상 지속 +1턴"},
    "독결정체":    {"name": "독의 결정체",  "stage": 2, "price": 130, "effect": {"poison_start": 3},   "desc": "전투 시작 시 적에게 중독 3스택"},
    "피의광기":    {"name": "피의 광기",    "stage": 2, "price": 160, "effect": {"atk": 7, "hp_drain": 8}, "desc": "ATK +7 / 매 전투 턴 HP -8"},
    # 신규 스테이지 2 (쌍)
    "독사이빨":    {"name": "독사의 이빨",  "stage": 2, "price": 120, "effect": {"poison_start": 4},   "desc": "전투 시작 시 적에게 중독 4스택"},
    "시간모래":    {"name": "시간의 모래",  "stage": 2, "price": 140, "effect": {"duration_bonus": 2}, "desc": "약화·취약·화상 지속 +2턴"},
}

# 유물 합성 조합 (키: 재료의 name 필드 튜플)
RELIC_SYNTHESIS = {
    ("숫돌",         "연습용 목검"): {"name": "날카로운 비수",  "effect": {"atk": 8},                            "desc": "공명: ATK +8"},
    ("가죽 망토",    "나무 방패"):   {"name": "수호자의 방패",  "effect": {"hp": 40},                            "desc": "공명: 최대 HP +40"},
    ("낡은 나침반",  "낡은 장화"):   {"name": "바람의 날개",    "effect": {"spd": 8},                            "desc": "공명: SPD +8"},
    ("마력 결정",    "마도사의 반지"):{"name": "마나의 원천",   "effect": {"bonus_energy": 3},                   "desc": "공명: 매 턴 에너지 +3"},
    ("화염의 징표",  "분노의 인장"): {"name": "불길의 맹약",    "effect": {"burn_start": 3, "atk": 4, "hp_drain": 4}, "desc": "공명: 화상 3턴 + ATK +4 / HP -4"},
    ("독사의 이빨",  "시간의 모래"): {"name": "영겁의 저주",    "effect": {"poison_start": 6, "duration_bonus": 3},   "desc": "공명: 중독 6스택 + 디버프 +3턴"},
}

# ── 5. 랜덤 사건 데이터 ──
RANDOM_EVENTS = [
    # 기존
    {
        "name": "오래된 샘터",
        "description": "반짝이는 맑은 물이 흐르는 샘터를 발견했습니다.",
        "choices": [
            {"text": "물을 마신다 (파티 전원 HP +20)",
             "result_text": "몸에 활력이 돕니다!",
             "effect": {"party_hp": 20}},
            {"text": "그냥 지나간다",
             "result_text": "아쉽지만 갈 길을 서두릅니다.",
             "effect": {}},
        ]
    },
    {
        "name": "떠돌이 상인의 짐수레",
        "description": "길가에 뒤집힌 수레에 물건들이 흩어져 있습니다.",
        "choices": [
            {"text": "수레를 뒤진다 (50G 획득 / 30% 확률로 함정 HP -10)",
             "result_text": "약간의 골드를 챙겼습니다!",
             "effect": {"gold": 50, "party_hp": -10, "chance": 0.3}},
            {"text": "지나친다",
             "result_text": "남의 물건에 손을 대지 않기로 합니다.",
             "effect": {}},
        ]
    },
    {
        "name": "버려진 무기 창고",
        "description": "먼지가 쌓인 창고에 날카로운 검들이 보입니다.",
        "choices": [
            {"text": "무기를 교체한다 (파티 ATK +2 영구)",
             "result_text": "공격력이 영구적으로 상승했습니다!",
             "effect": {"party_atk": 2}},
            {"text": "무시한다",
             "result_text": "현재 무기에 만족합니다.",
             "effect": {}},
        ]
    },
    # 신규 — 도박
    {
        "name": "도박사의 제안",
        "description": "교활한 눈빛의 인간 도박사가 금화를 튕깁니다. '50G만 걸어봐. 잃을 것도 없잖아?'",
        "choices": [
            {"text": "50G 배팅 (50% 확률로 2배, 실패 시 손실)",
             "result_text": "금화가 공중에서 반짝입니다...",
             "effect": {"gamble": {"bet": 50, "win_mult": 2, "win_chance": 0.5}}},
            {"text": "거절한다",
             "result_text": "도박사는 어깨를 으쓱하고 사라집니다.",
             "effect": {}},
        ]
    },
    # 신규 — 연속 도박 (작은 판돈, 높은 배율)
    {
        "name": "수상한 내기",
        "description": "낡은 모자를 쓴 짐승 상인이 속삭입니다. '20G면 돼. 세 배 줄게.'",
        "choices": [
            {"text": "20G 배팅 (40% 확률로 3배, 실패 시 손실)",
             "result_text": "숨을 죽이고 결과를 기다립니다...",
             "effect": {"gamble": {"bet": 20, "win_mult": 3, "win_chance": 0.4}}},
            {"text": "거절한다",
             "result_text": "위험한 내기는 하지 않기로 합니다.",
             "effect": {}},
        ]
    },
    # 신규 — 스탯 조정: 체력 ↓ 공격력 ↑
    {
        "name": "신비한 제단",
        "description": "검은 돌로 만들어진 제단이 낮은 목소리로 제안합니다. '선택하라, 탐험가여.'",
        "choices": [
            {"text": "체력을 제물로 (파티 HP -20, ATK +3 영구)",
             "result_text": "몸이 타오르는 고통과 함께 힘이 솟구칩니다.",
             "effect": {"party_hp": -20, "party_atk": 3}},
            {"text": "힘을 제물로 (ATK -2 영구, 파티 HP +30 회복)",
             "result_text": "상처가 빠르게 아물지만 팔에 힘이 빠집니다.",
             "effect": {"party_atk": -2, "party_hp": 30}},
            {"text": "외면한다",
             "result_text": "제단의 목소리가 잦아듭니다.",
             "effect": {}},
        ]
    },
    # 신규 — 확률 스탯 업/다운
    {
        "name": "운명의 갈림길",
        "description": "두 갈래 길 앞에서 목소리가 들립니다. '어느 쪽이 네 운명이냐?'",
        "choices": [
            {"text": "왼쪽 길 (60% ATK +4 / 40% HP -15)",
             "result_text": "길을 선택해 걸어갑니다.",
             "effect": {"gamble_stat": {"win_chance": 0.6,
                                        "win_effect":  {"party_atk": 4},
                                        "lose_effect": {"party_hp": -15}}}},
            {"text": "오른쪽 길 (70% HP +25 / 30% ATK -2)",
             "result_text": "길을 선택해 걸어갑니다.",
             "effect": {"gamble_stat": {"win_chance": 0.7,
                                        "win_effect":  {"party_hp": 25},
                                        "lose_effect": {"party_atk": -2}}}},
        ]
    },
    # 공용 카드 지급 사건
    {
        "name": "떠돌이 약초상",
        "description": "낡은 짐을 멘 약초상이 해독제를 내밀며 말합니다. '딱 20G야, 싸게 드리는 거야.'",
        "choices": [
            {"text": "20G에 구매 (해독제 카드 획득)",
             "result_text": "해독제를 손에 넣었습니다.",
             "effect": {"gold": -20, "give_card": "해독제"}},
            {"text": "그냥 지나간다",
             "result_text": "필요할 때 찾아오세요, 라는 말을 남기고 상인이 사라집니다.",
             "effect": {}},
        ]
    },
    {
        "name": "명상하는 수도승",
        "description": "동굴 깊숙이 가부좌를 튼 수도승이 손짓합니다. '집중하는 법을 가르쳐 주지.'",
        "choices": [
            {"text": "가르침을 받는다 (집중 카드 획득)",
             "result_text": "정신이 맑아지는 느낌입니다.",
             "effect": {"give_card": "집중"}},
            {"text": "거절한다",
             "result_text": "수도승이 조용히 눈을 감습니다.",
             "effect": {}},
        ]
    },
    {
        "name": "비밀 통로",
        "description": "벽 틈새로 이어지는 좁은 비밀 통로를 발견했습니다. 탈출 루트로 쓸 수 있을 것 같습니다.",
        "choices": [
            {"text": "통로를 기억해 둔다 (긴급 교대 카드 획득)",
             "result_text": "탈출 루트를 머릿속에 새겨 넣었습니다.",
             "effect": {"give_card": "긴급 교대"}},
            {"text": "그냥 지나간다",
             "result_text": "서두르느라 그냥 지나쳤습니다.",
             "effect": {}},
        ]
    },
    {
        "name": "마력의 샘",
        "description": "바위 틈에서 마력이 흘러나오는 신비한 샘을 발견했습니다. 흡수하면 기운을 빼앗길 것 같습니다.",
        "choices": [
            {"text": "마력을 흡수한다 (마나 회복 카드 획득, 파티 HP -10)",
             "result_text": "마력이 몸속으로 파고들어... 조금 기운이 빠집니다.",
             "effect": {"party_hp": -10, "give_card": "마나 회복"}},
            {"text": "그냥 지나간다",
             "result_text": "마력을 무시하고 발걸음을 옮깁니다.",
             "effect": {}},
        ]
    },
    # 신규 — 어둠의 거래 (큰 리스크)
    {
        "name": "어둠의 속삭임",
        "description": "그림자 속에서 목소리가 들립니다. '나에게 100G를 바쳐라. 그러면... 축복을 주지.'",
        "choices": [
            {"text": "100G를 바친다 (50% ATK+5·HP+20 / 50% 아무것도 없음)",
             "result_text": "어둠이 당신을 감쌉니다...",
             "effect": {"gamble": {"bet": 100, "win_mult": 0,
                                    "win_bonus": {"party_atk": 5, "party_hp": 20},
                                    "win_chance": 0.5}}},
            {"text": "무시한다",
             "result_text": "목소리가 비웃으며 사라집니다.",
             "effect": {}},
        ]
    },
]

# ── 헬퍼 함수 ──

def get_monster(name, floor):
    base  = copy.deepcopy(MONSTERS[name])
    scale = 1 + (floor * 0.1)
    base["hp"]  = int(base["base_hp"]  * scale)
    base["atk"] = int(base["base_atk"] * scale)
    base["spd"] = int(base["base_spd"] * (1 + floor * 0.05))
    return base

def get_boss(floor):
    base  = copy.deepcopy(BOSSES[floor])
    scale = 1 + (floor * 0.05)
    base["hp"]      = int(base["base_hp"]  * scale)
    base["atk"]     = int(base["base_atk"] * scale)
    base["spd"]     = base["base_spd"]
    base["is_boss"] = True
    return base

def get_class(name):
    return copy.deepcopy(CLASSES[name])

def get_stage_relics(stage, count=3):
    buyable = [r for r in RELICS.values() if r["stage"] == stage]
    return random.sample(buyable, min(count, len(buyable)))

def get_stage_monsters(stage):
    return [k for k, v in MONSTERS.items() if v.get("stage") == stage]

def get_random_event():
    return random.choice(RANDOM_EVENTS)

def get_monster_speech(name):
    m = MONSTERS.get(name) or next((v for v in BOSSES.values() if v["name"] == name), None)
    if m and "speech" in m:
        return m["speech"]
    return f"...{name}이(가) 으르렁거립니다."
