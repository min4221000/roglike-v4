# assets.py
import copy
import random

STAGE_INFO = {
    1: {"name": "초보자의 숲", "multiplier": 1.0},
    2: {"name": "어둠의 던전", "multiplier": 1.5}
}

def get_stage_by_floor(floor):
    if floor <= 15: return 1
    return 2

# 1. 직업 데이터 (전사, 마법사 고정)
CLASSES = {
    "전사": {
        "name": "전사", "hp": 120, "mp": 10, "atk": 1800, "defense": 8, "spd": 10,
        "type": "melee", # 근접: 기본 턴당 MP 1 회복
        "deck": ["강타", "강타", "강타", "방패막기", "방패막기", "전투의함성", "응급처치"]
    },
    "마법사": {
        "name": "마법사", "hp": 70, "mp": 20, "atk": 2200, "defense": 3, "spd": 12,
        "type": "ranged", # 원거리: 기본 턴당 MP 2 회복
        "deck": ["화염구", "화염구", "화염구", "마나폭발", "마법방어막", "번개화살", "치유의빛"]
    }
}

# 2. 카드 데이터 (직업 전용 분류)
CARDS = {
    # ── 전사 전용 ──
    "강타": {"name": "강타", "class": "전사", "cost": 3, "damage_mult": 1.5, "heal": 0, "target": "enemy", "effect": None, "description": "공격력의 1.5배 데미지."},
    "방패막기": {"name": "방패막기", "class": "전사", "cost": 4, "damage_mult": 0, "heal": 0, "target": "self", "effect": "def_up", "description": "3턴간 방어력 5 증가."},
    "연속베기": {"name": "연속베기", "class": "전사", "cost": 6, "damage_mult": 2.2, "heal": 0, "target": "enemy", "effect": None, "description": "공격력의 2.2배 강력한 베기."},
    "전투의함성": {"name": "전투의함성", "class": "전사", "cost": 8, "damage_mult": 0, "heal": 0, "target": "party", "effect": "atk_up", "description": "파티 전체 3턴간 공격력 20% 상승."},
    "응급처치": {"name": "응급처치", "class": "전사", "cost": 5, "damage_mult": 0, "heal": 25, "target": "ally", "effect": None, "description": "아군 1명 HP 25 회복."},
    
    # ── 마법사 전용 ──
    "화염구": {"name": "화염구", "class": "마법사", "cost": 5, "damage_mult": 1.8, "heal": 0, "target": "enemy", "effect": "burn", "description": "1.8배 데미지 + 화상(3턴) 부여."},
    "번개화살": {"name": "번개화살", "class": "마법사", "cost": 7, "damage_mult": 1.5, "heal": 0, "target": "enemy", "effect": "stun", "description": "1.5배 데미지 + 기절(1턴) 부여."},
    "마나폭발": {"name": "마나폭발", "class": "마법사", "cost": 12, "damage_mult": 2.5, "heal": 0, "target": "enemy_all", "effect": None, "description": "모든 적에게 2.5배 광역 데미지."},
    "마법방어막": {"name": "마법방어막", "class": "마법사", "cost": 6, "damage_mult": 0, "heal": 0, "target": "self", "effect": "def_up", "description": "3턴간 방어력 5 증가."},
    "치유의빛": {"name": "치유의빛", "class": "마법사", "cost": 6, "damage_mult": 0, "heal": 40, "target": "ally", "effect": None, "description": "아군 1명 HP 40 회복."},
}

# 3. 몬스터 데이터
# assets.py 내 MONSTERS 및 BOSSES 수정

MONSTERS = {
    # 1 스테이지: 늑대가 플레이어(10~12)보다 빨라 선공권 위협
    "고블린": {"name": "고블린", "stage": 1, "base_hp": 40, "base_atk": 8, "base_def": 2, "base_spd": 5, "pattern": ["normal", "power"], "reward_gold": 15},
    "늑대": {"name": "늑대", "stage": 1, "base_hp": 50, "base_atk": 11, "base_def": 1, "base_spd": 18, "pattern": ["normal", "quick", "normal"], "reward_gold": 20}, # 속도 18!
    
    # 2 스테이지: 해골전사는 느리지만 'quick(속공)' 패턴으로 기습함
    "해골전사": {"name": "해골전사", "stage": 2, "base_hp": 120, "base_atk": 18, "base_def": 8, "base_spd": 7, "pattern": ["normal", "quick", "power"], "reward_gold": 30},
    "불도마뱀": {"name": "불도마뱀", "stage": 2, "base_hp": 100, "base_atk": 22, "base_def": 5, "base_spd": 14, "pattern": ["normal", "fire_aoe"], "reward_gold": 35},
}

BOSSES = {
    15: {"name": "숲의 군주", "base_hp": 300, "base_atk": 25, "base_def": 10, "base_spd": 10, "pattern": ["normal", "power", "quick"], "reward_gold": 100},
    30: {"name": "심연의 근원", "base_hp": 600, "base_atk": 40, "base_def": 20, "base_spd": 22, "pattern": ["quick", "dark_slash", "aoe"], "reward_gold": 500},
}


# 4. 유물 데이터 (20종 + 마나재생 2종)
# assets.py 하단

RELICS = {
    "낡은나침반": {"name": "낡은 나침반", "stage": 1, "price": 40, "effect": {"spd": 2}, "desc": "SPD +2"},
    "약초주머니": {"name": "약초 주머니", "stage": 1, "price": 50, "effect": {"hp": 15}, "desc": "최대 HP +15"},
    "숫돌": {"name": "숫돌", "stage": 1, "price": 60, "effect": {"atk": 2}, "desc": "ATK +2"},
    "가죽망토": {"name": "가죽 망토", "stage": 1, "price": 55, "effect": {"defense": 2}, "desc": "DEF +2"},
    "나무방패": {"name": "나무 방패", "stage": 1, "price": 65, "effect": {"defense": 3}, "desc": "DEF +3"},
    "연습용목검": {"name": "연습용 목검", "stage": 1, "price": 70, "effect": {"atk": 3}, "desc": "ATK +3"},
    "낡은장화": {"name": "낡은 장화", "stage": 1, "price": 45, "effect": {"spd": 3}, "desc": "SPD +3"},
    "명상용향로": {"name": "명상용 향로", "stage": 1, "price": 60, "effect": {"mp": 5}, "desc": "최대 EN +5"},
    "행운의동전": {"name": "행운의 동전", "stage": 1, "price": 50, "effect": {"atk": 1, "spd": 1}, "desc": "ATK +1, SPD +1"},
    "마나파편": {"name": "마나 수정 파편", "stage": 1, "price": 60, "effect": {"mp_regen": 1}, "desc": "매 턴 EN 회복량 +1"},
    "기사의휘장": {"name": "기사의 휘장", "stage": 2, "price": 100, "effect": {"atk": 5}, "desc": "ATK +5"},
    "강철갑옷": {"name": "강철 갑옷", "stage": 2, "price": 110, "effect": {"defense": 5}, "desc": "DEF +5"},
    "마도사의반지": {"name": "마도사의 반지", "stage": 2, "price": 150, "effect": {"mp_regen": 2}, "desc": "매 턴 EN 회복량 +2"},
    "거인의심장": {"name": "거인의 심장", "stage": 2, "price": 150, "effect": {"hp": 40}, "desc": "최대 HP +40"}
}

RELIC_SYNTHESIS = {
    ("숫돌", "연습용 목검"): {"name": "날카로운 비수", "effect": {"atk": 8}, "desc": "공명: ATK +8"},
    ("가죽 망토", "나무 방패"): {"name": "수호자의 방패", "effect": {"defense": 7}, "desc": "공명: DEF +7"},
    ("낡은 나침반", "낡은 장화"): {"name": "바람의 날개", "effect": {"spd": 8}, "desc": "공명: SPD +8"},
    ("마나 수정 파편", "명상용 향로"): {"name": "마나의 원천", "effect": {"mp_regen": 2, "mp": 10}, "desc": "공명: Regen +2, EN +10"}
}
def get_stage_relics(stage, count=2):
    import random
    available = [v for k, v in RELICS.items() if v['stage'] == stage]
    return random.sample(available, min(count, len(available)))

# assets.py 맨 아래에 추가

# 6. 랜덤 사건 데이터 (Random Events)
RANDOM_EVENTS = [
    {
        "name": "오래된 샘터",
        "description": "반짝이는 맑은 물이 흐르는 샘터를 발견했습니다. 갈증이 해소될 것 같습니다.",
        "choices": [
            {"text": "물을 마신다 (파티 전원 HP +20)", "result_text": "몸에 활력이 돕니다!", "effect": {"party_hp": 20}},
            {"text": "그냥 지나간다", "result_text": "아쉽지만 갈 길을 서두릅니다.", "effect": {}}
        ]
    },
    {
        "name": "떠돌이 상인의 짐수레",
        "description": "길가에 주인이 없는 듯한 수레가 뒤집혀 있습니다. 몇몇 물건들이 흩어져 있습니다.",
        "choices": [
            {"text": "수레를 뒤진다 (50G 획득 / 30% 확률로 함정 HP -10)", "result_text": "약간의 골드를 챙겼습니다!", "effect": {"gold": 50, "party_hp": -5}},
            {"text": "지나친다", "result_text": "남의 물건에 손을 대지 않기로 합니다.", "effect": {}}
        ]
    },
    {
        "name": "버려진 무기 창고",
        "description": "먼지가 쌓인 창고 안에 아직 날카로운 검들이 몇 자루 보입니다.",
        "choices": [
            {"text": "무기를 교체한다 (파티 전체 ATK +2)", "result_text": "공격력이 영구적으로 상승했습니다!", "effect": {"party_atk": 2}},
            {"text": "무시한다", "result_text": "현재 무기에 만족합니다.", "effect": {}}
        ]
    }
]


# get_monster 함수에서 스피드 스케일링 추가
def get_monster(name, floor):
    stage = get_stage_by_floor(floor)
    base = copy.deepcopy(MONSTERS[name])
    scale = 1 + (floor * 0.1)
    base["hp"] = int(base["base_hp"] * scale)
    base["atk"] = int(base["base_atk"] * scale)
    base["defense"] = int(base["base_def"] * scale)
    base["spd"] = int(base.get("base_spd", 5) * (1 + floor * 0.05)) # 스피드도 조금씩 상승
    return base

def get_boss(floor):
    base = copy.deepcopy(BOSSES[floor])
    scale = 1 + (floor * 0.05)
    base["hp"] = int(base["base_hp"] * scale)
    base["atk"] = int(base["base_atk"] * scale)
    base["defense"] = int(base["base_def"] * scale)
    return base

def get_class(name): return copy.deepcopy(CLASSES[name])
def get_stage_relics(stage, count=3):
    buyable = [r for r in RELICS.values() if r["stage"] == stage]
    return random.sample(buyable, min(count, len(buyable)))
def get_stage_monsters(stage): return [n for n, d in MONSTERS.items() if d["stage"] == stage]
# assets.py 맨 아래에 추가
def get_random_event():
    """랜덤 사건을 반환합니다."""
    return random.choice(RANDOM_EVENTS)

def get_monster_speech(name):
    """몬스터의 대사를 반환합니다."""
    return f"크르르... {name}이(가) 너희를 삼켜버리겠다!"

def get_stage_monsters(stage):
    """해당 스테이지의 몬스터 목록을 반환합니다."""
    return [k for k, v in MONSTERS.items() if v.get('stage') == stage]