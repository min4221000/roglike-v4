# combat.py
import time
import random
import assets
from assets import STATUS_INFO
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

# ── 상태이상 초기화 ──

def _init_statuses(entity):
    if 'statuses' not in entity:
        entity['statuses'] = {}

# ── 스탯 계산 ──

def get_effective_stat(entity, stat_name):
    """버프/디버프가 반영된 실제 능력치를 반환합니다."""
    _init_statuses(entity)
    val = entity.get(stat_name, 0)

    if stat_name == 'atk':
        if entity['statuses'].get('atk_up', 0) > 0:
            val = int(val * 1.2)   # 공격 강화: +20%
        if entity['statuses'].get('weak', 0) > 0:
            val = int(val * 0.75)  # 약화: -25%

    return val

def _apply_def_up(dmg, defender):
    """방어막 상태이상: 받는 피해 30% 감소. 카드 효과로만 발동."""
    if defender.get('statuses', {}).get('def_up', 0) > 0:
        dmg = int(dmg * 0.7)
    return dmg

def _calc_dmg(attacker, defender, mult=1.0):
    """약화/방어막/취약을 모두 반영한 최종 피해량을 계산합니다."""
    atk = get_effective_stat(attacker, 'atk')
    raw = max(1, int(atk * mult))
    dmg = _apply_def_up(raw, defender)
    return _apply_vulnerable(dmg, defender)

def _apply_vulnerable(dmg, target):
    """취약 상태이상이 걸린 대상에게 피해 50% 추가 적용."""
    _init_statuses(target)
    if target['statuses'].get('vulnerable', 0) > 0:
        dmg = int(dmg * 1.5)
    return dmg

# ── 상태이상 처리 ──

def process_turn_statuses(entity):
    """턴 종료 시 지속 상태이상을 처리하고 지속 시간을 1씩 감소시킵니다."""
    _init_statuses(entity)
    expired = []

    for status, turns in list(entity['statuses'].items()):
        if turns <= 0:
            expired.append(status)
            continue

        # stun은 _monster_turn_logic에서 행동 시 직접 소비 — 여기서 틱다운 안 함
        if status == 'stun':
            continue

        if status == 'burn':
            dmg = 5
            entity['current_hp'] = max(0, entity['current_hp'] - dmg)
            console.print(f"  [bold red]불 화상! {entity['name']}이(가) {dmg}의 피해를 입었습니다.[/bold red]")

        elif status == 'poison':
            dmg = turns
            entity['current_hp'] = max(0, entity['current_hp'] - dmg)
            console.print(f"  [bold green]중독! {entity['name']}이(가) {dmg}의 피해를 입었습니다. (남은 스택: {turns - 1})[/bold green]")

        entity['statuses'][status] -= 1
        if entity['statuses'][status] <= 0:
            expired.append(status)

    for s in expired:
        del entity['statuses'][s]

def _status_display(entity):
    """상태이상 목록을 STATUS_INFO의 한글 이름으로 포맷해 반환합니다."""
    parts = []
    for key, val in entity.get('statuses', {}).items():
        if val > 0:
            korean_name = STATUS_INFO.get(key, {}).get('name', key.upper())
            parts.append(f"[bold yellow]{korean_name}({val})[/bold yellow]")
    return " ".join(parts)

# ── 인텐트 ──

def _get_intent_text(monster, action):
    """몬스터 행동 패턴 코드를 사람이 읽기 좋은 예고 문구로 변환합니다."""
    base_dmg = get_effective_stat(monster, 'atk')
    intent_map = {
        'normal':            f"[red]일반 공격[/red]       (약 {base_dmg} 피해)",
        'power':             f"[bold red]강타[/bold red]           (약 {int(base_dmg * 1.5)} 피해)",
        'quick':             f"[yellow]속공 선제[/yellow]     (약 {int(base_dmg * 0.8)} 피해)",
        'dark_slash':        f"[magenta]암흑 베기[/magenta]    (약 {int(base_dmg * 2.0)} 피해)",
        'fire_aoe':          f"[red]광역 화염[/red]       (약 {int(base_dmg * 0.7)} 피해 x 전원)",
        'aoe':               f"[red]광역 공격[/red]       (약 {int(base_dmg * 1.1)} 피해 x 전원)",
        'poison_bite':       f"[green]독 이빨[/green]        (약 {int(base_dmg * 0.6)} 피해 + 중독 2스택)",
        'weaken_slash':      f"[yellow]약화 베기[/yellow]     (약 {int(base_dmg * 0.8)} 피해 + 약화 2턴)",
        'vulnerable_strike': f"[magenta]취약 강타[/magenta]    (약 {base_dmg} 피해 + 취약 2턴)",
        'poison_aoe':        f"[green]독 안개[/green]        (전원 약 {int(base_dmg * 0.4)} 피해 + 중독 2스택)",
    }
    return intent_map.get(action, "행동 준비 중")

# ── 화면 렌더링 ──

def _energy_display(char):
    """에너지 표시. 과다충전(후방 충전 후 스왑) 상태면 노란색으로 강조합니다."""
    cur = char['current_energy']
    mp  = char['mp']
    if cur > mp:
        return f"EN [bold yellow]{cur}[/bold yellow]/[dim]{mp}[/dim]  [yellow]과충전![/yellow]"
    return f"EN [cyan]{cur}/{mp}[/cyan]"

def _hp_bar(cur, max_hp, length=20):
    ratio = max(cur, 0) / max(max_hp, 1)
    color = "green" if ratio > 0.5 else "yellow" if ratio > 0.25 else "red"
    filled = int(ratio * length)
    return f"[{color}]{'█' * filled}[/{color}][dim]{'░' * (length - filled)}[/dim]"

def draw_combat_screen(player, monster, turn, intent=None):
    """전투 화면을 다시 그립니다. intent가 있으면 적 패널에 예고 행동을 표시합니다."""
    console.clear()
    console.print(Panel(
        f" 턴 {turn}  |  {player.gold}G  |  {player.current_floor}층",
        box=box.HORIZONTALS, style="dim white"
    ))

    # 적 패널 (인텐트 포함)
    m_table = Table.grid(padding=(0, 1))
    m_table.add_column(width=30)
    m_table.add_column()
    m_table.add_row(
        f"[bold red]{monster['name']}[/bold red]",
        f"{_hp_bar(monster['current_hp'], monster['hp'])} [white]{monster['current_hp']}/{monster['hp']}[/white]"
    )
    m_table.add_row(
        f"[dim]ATK {monster.get('atk','?')}  SPD {monster.get('spd','?')}[/dim]",
        ""
    )
    m_status = _status_display(monster)
    if m_status:
        m_table.add_row("", f"상태: {m_status}")
    if intent:
        m_table.add_row("", f"[dim]예고:[/dim] {intent}")
    console.print(Panel(m_table, title="[red]ENEMY[/red]", box=box.ROUNDED, style="red"))

    # 아군 패널
    p_table = Table.grid(padding=(0, 2))
    p_table.add_column(width=12)
    p_table.add_column(width=15)
    p_table.add_column()
    p_table.add_column()

    for i, char in enumerate(player.party):
        mark    = "[bold green]전방[/bold green]" if i == player.active_index else "[dim]  후방[/dim]"
        buffs   = _status_display(char)
        name_line = f"[bold]{char['name']}[/bold]" + (f"\n{buffs}" if buffs else "")
        p_table.add_row(
            mark,
            name_line,
            f"{_hp_bar(char['current_hp'], char['hp'])} {char['current_hp']}/{char['hp']}",
            _energy_display(char)
        )
    console.print(Panel(p_table, title="[green]PARTY[/green]", box=box.ROUNDED, style="green"))

# ── 전투 메인 루프 ──

def _check_player_alive(player):
    """전방 캐릭터 사망 시 후방으로 강제 스왑. 전멸이면 False 반환."""
    if player.active_char['current_hp'] > 0:
        return True

    other_index = 1 - player.active_index
    if player.party[other_index]['current_hp'] > 0:
        dead_name = player.active_char['name']
        player.active_index = other_index
        console.print(
            f"\n[bold red]{dead_name} 전사![/bold red] "
            f"[yellow]{player.active_char['name']}(으)로 긴급 교체![/yellow]"
        )
        time.sleep(1.5)
        return True

    return False  # 파티 전멸

def run_combat(player, monster):
    turn = 1
    player.init_combat_decks()
    _init_statuses(monster)

    # 유물 전투 시작 효과
    poison_stacks = sum(r.get('effect', {}).get('poison_start', 0) for r in player.relics)
    if poison_stacks > 0:
        monster['statuses']['poison'] = poison_stacks
        console.print(f"[bold green]중독 유물 발동! {monster['name']}에게 중독 {poison_stacks}스택![/bold green]")
        time.sleep(0.8)

    burn_turns = sum(r.get('effect', {}).get('burn_start', 0) for r in player.relics)
    if burn_turns > 0:
        monster['statuses']['burn'] = max(monster['statuses'].get('burn', 0), burn_turns)
        console.print(f"[bold red]화염 유물 발동! {monster['name']}에게 화상 {burn_turns}턴![/bold red]")
        time.sleep(0.8)

    pattern = monster.get('pattern', ['normal'])

    while True:
        active = player.active_char
        player.reset_energy()      # 슬더스식: 매 턴 에너지를 mp + 유물 보너스로 리셋
        player.draw_cards(active, 4)

        # hp_drain 유물: 매 턴 시작 시 전방 HP 소모 (피의 서약 등)
        total_drain = sum(r.get('effect', {}).get('hp_drain', 0) for r in player.relics)
        if total_drain > 0 and active['current_hp'] > 1:
            active['current_hp'] = max(1, active['current_hp'] - total_drain)
            drain_names = ", ".join(r['name'] for r in player.relics if r.get('effect', {}).get('hp_drain', 0) > 0)
            console.print(f"  [dim red]{drain_names} — {active['name']} HP -{total_drain}[/dim red]")
            time.sleep(0.4)

        # 이번 턴 행동 결정 (turn=1이 index 0부터 시작하도록 -1 보정)
        current_action = pattern[(turn - 1) % len(pattern)]
        # 다음 턴 행동 (플레이어가 대비할 수 있도록 미리 보여줌)
        next_action = pattern[turn % len(pattern)]

        # 속도 비교로 선공 결정
        monster_first = False
        if current_action == "quick":
            monster_first = True
            priority_msg = "[bold yellow]경고! 적이 속공 기습을 준비합니다![/bold yellow]"
        elif monster.get('spd', 5) > active.get('spd', 10):
            monster_first = True
            priority_msg = f"[bold red]적이 더 빠릅니다! (적:{monster.get('spd','?')} vs 나:{active.get('spd','?')})[/bold red]"
        else:
            priority_msg = f"[bold green]내가 더 빠릅니다! (나:{active.get('spd','?')} vs 적:{monster.get('spd','?')})[/bold green]"

        if monster_first:
            # 몬스터가 먼저 공격 → 플레이어 행동 시엔 "다음 턴" 예고를 보여줌
            current_intent = _get_intent_text(monster, current_action)
            draw_combat_screen(player, monster, turn, current_intent)
            console.print(f"  {priority_msg}")
            _monster_turn_logic(monster, player.active_char, player, current_action)
            if not _check_player_alive(player):
                return False

            next_intent = _get_intent_text(monster, next_action)
            if not _player_turn_logic(player, monster, turn, next_intent):
                return True
        else:
            # 플레이어가 먼저 행동 → "이번 턴" 몬스터 행동을 인텐트로 표시
            current_intent = _get_intent_text(monster, current_action)
            draw_combat_screen(player, monster, turn, current_intent)
            console.print(f"  {priority_msg}")
            if not _player_turn_logic(player, monster, turn, current_intent):
                return True

            _monster_turn_logic(monster, player.active_char, player, current_action)
            if not _check_player_alive(player):
                return False

        # 턴 종료: 상태이상 처리
        process_turn_statuses(player.active_char)
        if not _check_player_alive(player):  # 화상/중독으로 플레이어 사망 시
            return False

        process_turn_statuses(monster)
        if monster['current_hp'] <= 0:      # 화상/중독으로 몬스터 사망 시
            _victory_sequence(player, monster)
            return True

        turn += 1
        time.sleep(1)

# ── 플레이어 행동 ──

def _player_turn_logic(player, monster, turn, intent):
    """플레이어 행동 단계.
    에너지가 남아있는 한 카드를 여러 장 사용할 수 있습니다.
    평타 또는 턴 종료 선택 시 턴이 끝납니다.
    몬스터가 사망하면 False를 반환해 전투 종료를 알립니다."""

    swap_used = False  # 턴당 스왑 1회 제한

    while True:
        active = player.active_char
        draw_combat_screen(player, monster, turn, intent)

        active = player.active_char
        energy = active['current_energy']
        other  = player.party[1 - player.active_index]
        other_alive = other['current_hp'] > 0

        if swap_used:
            swap_label = "[dim]2. 스왑 (이미 사용)[/dim]"
        elif not other_alive:
            swap_label = f"[dim]2. 스왑 ({other['name']} 전사)[/dim]"
        else:
            swap_label = "[bold cyan]2.[/bold cyan] 스왑"

        console.print(
            f"\n  [bold cyan]1.[/bold cyan] 카드 사용 [dim](EN {energy} 남음)[/dim]   "
            f"{swap_label}   "
            f"[bold cyan]3.[/bold cyan] 턴 종료\n"
        )
        cmd = console.input("  선택: ").strip()

        if cmd == '1':
            side_effects = _handle_card_use(player, monster, active)
            if side_effects and side_effects.get('swap_free'):
                other = player.party[1 - player.active_index]
                if other['current_hp'] > 0:
                    player.swap()
                    new_active = player.active_char
                    player.draw_cards(new_active, 4)
                    # swap_used는 소비하지 않음
                else:
                    console.print(f"  [red]교체할 수 있는 아군이 없습니다![/red]")
                    time.sleep(0.6)
            turn_over = False

        elif cmd == '2':
            if swap_used:
                console.print("  [red]이미 이번 턴에 스왑했습니다![/red]")
                time.sleep(0.6)
                turn_over = False
            elif not other_alive:
                console.print(f"  [red]{other['name']}은(는) 전사해서 스왑할 수 없습니다.[/red]")
                time.sleep(0.6)
                turn_over = False
            else:
                player.swap()
                new_active = player.active_char
                player.draw_cards(new_active, 4)
                console.print(f"  [cyan]{new_active['name']}(으)로 교체되었습니다![/cyan]")
                swap_used = True
                time.sleep(0.8)
                turn_over = False

        elif cmd == '3':
            turn_over = True

        else:
            turn_over = False

        # 몬스터 사망 체크 (카드 사용 후 즉시 확인)
        if monster['current_hp'] <= 0:
            _victory_sequence(player, monster)
            return False  # 전투 종료 (승리)

        if turn_over:
            break

    return True  # 전투 계속

def _handle_card_use(player, monster, active):
    """카드 선택 인터페이스. 사용 성공 시 True, 취소 시 False 반환."""
    if not active['hand']:
        remaining = len(active['draw_pile'])
        console.print(f"\n  [red]손패가 없습니다.[/red] [dim](드로우 파일 잔여: {remaining}장)[/dim]")
        time.sleep(0.8)
        return False

    console.print("\n  [cyan]현재 손패[/cyan]")
    for i, card_name in enumerate(active['hand'], 1):
        card = assets.CARDS.get(card_name, {})
        console.print(f"    {i}. [bold]{card_name}[/bold] (EN:{card['cost']}) - [dim]{card['description']}[/dim]")
    console.print("    0. 뒤로가기")

    try:
        idx = int(console.input("\n  사용할 카드 번호: ")) - 1
        if idx == -1:
            return False

        card_name = active['hand'][idx]
        card = assets.CARDS[card_name]

        if active['current_energy'] < card['cost']:
            console.print("  [red]에너지가 부족합니다![/red]")
            time.sleep(0.8)
            return False

        active['current_energy'] -= card['cost']
        active['discard_pile'].append(active['hand'].pop(idx))
        side_effects = _execute_card_effects(card, active, player, monster)
        time.sleep(1.2)
        return side_effects

    except (ValueError, IndexError):
        return False

def _execute_card_effects(card, active, player, monster):
    """카드 효과를 순서대로 적용합니다: 피해 → 상태이상/버프 → 회복 → 공용 효과."""
    console.print(f"\n  [bold cyan]'{card['name']}' 발동![/bold cyan]")
    effect = card.get('effect')
    dur_bonus = sum(r.get('effect', {}).get('duration_bonus', 0) for r in player.relics)
    side_effects = {}

    # 1. 피해 (상태이상 부여 전에 먼저 처리)
    if card.get('damage_mult', 0) > 0:
        dmg = _calc_dmg(active, monster, card['damage_mult'])

        if card['target'] == 'enemy_all':
            monster['current_hp'] -= dmg
            console.print(f"  [bold red]광역 폭발! {monster['name']}에게 {dmg}의 피해![/bold red]")
        else:
            monster['current_hp'] -= dmg
            console.print(f"  [bold red]{monster['name']}에게 {dmg}의 피해![/bold red]")

    # 2. 상태이상 / 버프 / 디버프 부여
    if effect == 'atk_up':
        for c in player.party:
            _init_statuses(c)
            c['statuses']['atk_up'] = max(c['statuses'].get('atk_up', 0), 3)
        console.print("  [yellow]파티 전체 공격력 상승! (3턴)[/yellow]")

    elif effect == 'def_up':
        _init_statuses(active)
        active['statuses']['def_up'] = max(active['statuses'].get('def_up', 0), 3)
        console.print(f"  [blue]{active['name']}의 방어막! (3턴)[/blue]")

    elif effect == 'weak':
        _init_statuses(monster)
        monster['statuses']['weak'] = max(monster['statuses'].get('weak', 0), 2 + dur_bonus)
        console.print(f"  [yellow]{monster['name']} 약화! 공격력 25% 감소 ({2 + dur_bonus}턴)[/yellow]")

    elif effect == 'vulnerable':
        _init_statuses(monster)
        monster['statuses']['vulnerable'] = max(monster['statuses'].get('vulnerable', 0), 2 + dur_bonus)
        console.print(f"  [magenta]{monster['name']} 취약! 받는 피해 50% 증가 ({2 + dur_bonus}턴)[/magenta]")

    elif effect == 'poison':
        _init_statuses(monster)
        # 중독만 스택 누적
        monster['statuses']['poison'] = monster['statuses'].get('poison', 0) + 3
        total = monster['statuses']['poison']
        console.print(f"  [bold green]{monster['name']}에게 중독 3스택! (총 {total}스택)[/bold green]")

    elif effect == 'burn':
        _init_statuses(monster)
        monster['statuses']['burn'] = max(monster['statuses'].get('burn', 0), 3 + dur_bonus)
        console.print(f"  [red]{monster['name']}에게 화상! ({3 + dur_bonus}턴)[/red]")

    elif effect == 'stun':
        if monster.get('is_boss', False):
            console.print(f"  [dim]{monster['name']}은(는) 기절에 면역입니다![/dim]")
        elif random.random() < 0.5:   # 50% 확률
            _init_statuses(monster)
            monster['statuses']['stun'] = max(monster['statuses'].get('stun', 0), 1)
            console.print(f"  [bold yellow]{monster['name']} 기절![/bold yellow]")
        else:
            console.print(f"  [bold yellow]{monster['name']}이(가) 기절을 버텼습니다![/bold yellow]")
            time.sleep(0.5)

    # 3. 회복
    if card.get('heal', 0) > 0:
        heal_amt = card['heal']
        if card['target'] == 'ally':
            console.print("  누구를 치료할까요? [1] 전사  [2] 마법사")
            try:
                t_idx = int(console.input("  대상: ")) - 1
                target = player.party[t_idx]
            except (ValueError, IndexError):
                target = active
            target['current_hp'] = min(target['hp'], target['current_hp'] + heal_amt)
            console.print(f"  [green]{target['name']}의 체력 {heal_amt} 회복![/green]")

    # 4. 공용 카드 효과
    if effect == 'mp_restore':
        restore = random.randint(2, 3)
        active['current_energy'] += restore
        console.print(f"  [cyan]{active['name']} 에너지 +{restore}! (현재: {active['current_energy']})[/cyan]")

    elif effect == 'draw2':
        drawn = player.draw_cards_add(active, 2)
        console.print(f"  [cyan]{active['name']} — 카드 {drawn}장 추가 드로우![/cyan]")

    elif effect == 'cleanse':
        NEGATIVE = {'burn', 'poison', 'stun', 'vulnerable', 'weak'}
        alive = [c for c in player.party if c['current_hp'] > 0]
        if len(alive) == 1:
            target = alive[0]
        else:
            console.print(f"  해독 대상: [1] {player.party[0]['name']}  [2] {player.party[1]['name']}")
            try:
                t_idx = int(console.input("  대상: ")) - 1
                target = player.party[t_idx] if player.party[t_idx]['current_hp'] > 0 else alive[0]
            except (ValueError, IndexError):
                target = active
        neg = {k: v for k, v in target.get('statuses', {}).items() if k in NEGATIVE and v > 0}
        if not neg:
            console.print(f"  [dim]{target['name']}에게 제거할 상태이상이 없습니다.[/dim]")
        else:
            worst = max(neg, key=neg.get)
            del target['statuses'][worst]
            korean = STATUS_INFO.get(worst, {}).get('name', worst)
            console.print(f"  [green]{target['name']}의 {korean} 해제![/green]")

    elif effect == 'swap_free':
        side_effects['swap_free'] = True

    return side_effects

# ── 몬스터 행동 ──

def _monster_turn_logic(monster, active, player, action):
    """몬스터 공격 단계. 기절 상태이면 아무것도 하지 않습니다."""
    _init_statuses(monster)

    if monster['statuses'].get('stun', 0) > 0:
        console.print(f"\n  [bold yellow]{monster['name']}은(는) 기절해 움직이지 못합니다![/bold yellow]")
        # 기절 1회 소비 (턴 틱다운이 아닌 행동 시 소비)
        monster['statuses']['stun'] -= 1
        if monster['statuses']['stun'] <= 0:
            del monster['statuses']['stun']
        return

    # ── 상태이상 부여 행동 (피해 + 디버프) ──
    if action == "poison_bite":
        dmg = _calc_dmg(monster, active, 0.6)
        active['current_hp'] -= dmg
        _init_statuses(active)
        active['statuses']['poison'] = active['statuses'].get('poison', 0) + 2
        console.print(f"\n  [bold green]{monster['name']}의 독 이빨![/bold green]")
        console.print(f"  [red]{active['name']}에게 {dmg} 피해![/red] [green]중독 2스택![/green]")
        time.sleep(1.2)
        return

    if action == "weaken_slash":
        dmg = _calc_dmg(monster, active, 0.8)
        active['current_hp'] -= dmg
        _init_statuses(active)
        active['statuses']['weak'] = max(active['statuses'].get('weak', 0), 2)
        console.print(f"\n  [bold yellow]{monster['name']}의 약화 베기![/bold yellow]")
        console.print(f"  [red]{active['name']}에게 {dmg} 피해![/red] [yellow]약화 2턴![/yellow]")
        time.sleep(1.2)
        return

    if action == "vulnerable_strike":
        dmg = _calc_dmg(monster, active, 1.0)
        active['current_hp'] -= dmg
        _init_statuses(active)
        active['statuses']['vulnerable'] = max(active['statuses'].get('vulnerable', 0), 2)
        console.print(f"\n  [bold magenta]{monster['name']}의 취약 강타![/bold magenta]")
        console.print(f"  [red]{active['name']}에게 {dmg} 피해![/red] [magenta]취약 2턴![/magenta]")
        time.sleep(1.2)
        return

    # ── 광역 행동 ──
    if action == "poison_aoe":
        console.print(f"\n  [bold green]{monster['name']}의 독 안개![/bold green]")
        for c in player.party:
            dmg = _calc_dmg(monster, c, 0.4)
            c['current_hp'] -= dmg
            _init_statuses(c)
            c['statuses']['poison'] = c['statuses'].get('poison', 0) + 2
            console.print(f"    {c['name']}에게 {dmg} 피해! [green]중독 2스택[/green]")
        time.sleep(1.2)
        return

    if action == "fire_aoe":
        console.print(f"\n  [bold red]{monster['name']}의 광역 화염![/bold red]")
        for c in player.party:
            dmg = _calc_dmg(monster, c, 0.7)
            c['current_hp'] -= dmg
            console.print(f"    {c['name']}에게 {dmg} 피해!")
        time.sleep(1.2)
        return

    if action == "aoe":
        console.print(f"\n  [bold red]{monster['name']}의 광역 공격![/bold red]")
        for c in player.party:
            dmg = _calc_dmg(monster, c, 1.1)
            c['current_hp'] -= dmg
            console.print(f"    {c['name']}에게 {dmg} 피해!")
        time.sleep(1.2)
        return

    # ── 단일 공격 ──
    mult_map = {
        "quick":      (0.8, f"[bold yellow]속공! {monster['name']}이 번개처럼 달려듭니다![/bold yellow]"),
        "power":      (1.5, f"[bold red]{monster['name']}의 강력한 강타![/bold red]"),
        "dark_slash": (2.0, f"[bold magenta]{monster['name']}의 암흑 베기![/bold magenta]"),
        "normal":     (1.0, f"[bold red]{monster['name']}의 공격![/bold red]"),
    }
    mult, msg = mult_map.get(action, mult_map["normal"])

    dmg = _calc_dmg(monster, active, mult)
    console.print(f"\n  {msg}")
    active['current_hp'] -= dmg
    console.print(f"  [red]{active['name']}에게 {dmg} 피해![/red]")
    time.sleep(1.2)

# ── 전투 승리 및 보상 ──

def _victory_sequence(player, monster):
    """전투 승리 처리: 골드 지급 후 카드 보상 이벤트 진행."""
    console.clear()
    base = monster.get('reward_gold', 20)
    gold = random.randint(int(base * 0.8), int(base * 1.2))  # ±20% 랜덤 변동
    player.gold += gold
    console.print(Panel(
        f"[bold green]승리! {monster['name']}을(를) 물리쳤습니다![/bold green]\n"
        f"획득: [yellow]+{gold}G[/yellow]   보유: [yellow]{player.gold}G[/yellow]",
        box=box.DOUBLE
    ))
    time.sleep(1.5)
    _card_reward_event(player)

def _card_reward_event(player):
    """직업 전용 카드 3장 중 1장을 덱에 추가하는 보상 이벤트."""
    char = player.active_char
    class_cards = [k for k, v in assets.CARDS.items() if v['class'] == char['name']]
    choices = random.sample(class_cards, min(3, len(class_cards)))

    console.print(f"\n[bold yellow]새로운 기술을 발견했습니다! ({char['name']})[/bold yellow]\n")
    for i, card_name in enumerate(choices, 1):
        card = assets.CARDS[card_name]
        console.print(f"  {i}. [cyan]{card['name']}[/] (EN:{card['cost']}) - {card['description']}")
    console.print("  0. 스킵")

    while True:
        cmd = console.input("\n번호 선택: ").strip()
        if cmd == '0':
            break
        if cmd in [str(j) for j in range(1, len(choices) + 1)]:
            new_card = choices[int(cmd) - 1]

            # 덱이 15장이면 버릴 카드 선택
            if len(char['deck']) >= 15:
                console.print("\n[red]덱이 꽉 찼습니다 (최대 15장). 버릴 카드를 선택하세요:[/red]")
                for idx, name in enumerate(char['deck'], 1):
                    console.print(f"  {idx}. {name}")
                try:
                    drop = int(console.input("번호: ")) - 1
                    char['deck'].pop(drop)
                except (ValueError, IndexError):
                    continue

            char['deck'].append(new_card)
            console.print(f"[bold green]'{new_card}' 카드가 덱에 추가되었습니다![/bold green]")
            break

    time.sleep(1)
