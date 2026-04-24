import time
import random
import assets
from rich.console import Console, Group # Group을 여기서 가져오세요!
from rich.panel import Panel
from rich.table import Table



console = Console()

# ── 상태이상 및 스탯 관리 ──
def _init_statuses(entity):
    if 'statuses' not in entity:
        entity['statuses'] = {}

def get_effective_stat(entity, stat_name):
    """버프/디버프가 적용된 실제 능력치를 계산합니다."""
    _init_statuses(entity)
    val = entity.get(stat_name, 0)
    # 공격력 증가 (20%)
    if stat_name == 'atk' and entity['statuses'].get('atk_up', 0) > 0:
        val = int(val * 1.2)
    # 방어력 증가 (+5)
    elif stat_name == 'defense' and entity['statuses'].get('def_up', 0) > 0:
        val += 5
    return val

def process_turn_statuses(entity):
    """턴 종료 시 상태이상을 처리하고 지속 시간을 감소시킵니다."""
    _init_statuses(entity)
    expired = []
    for status, turns in entity['statuses'].items():
        if turns > 0:
            if status == 'burn':
                dmg = 5
                entity['current_hp'] = max(0, entity['current_hp'] - dmg)
                console.print(f"  [bold red]🔥 화상! {entity['name']}이(가) {dmg}의 피해를 입었습니다.[/bold red]")
            entity['statuses'][status] -= 1
            if entity['statuses'][status] <= 0:
                expired.append(status)
    for s in expired:
        del entity['statuses'][s]

def _hp_bar(cur, max_hp, length=20):
    ratio = max(cur, 0) / max(max_hp, 1)
    color = "green" if ratio > 0.5 else "yellow" if ratio > 0.25 else "red"
    filled = int(ratio * length)
    return f"[{color}]{'█' * filled}[/{color}][dim]{'░' * (length - filled)}[/dim]"

def draw_combat_screen(player, monster, turn):
    """전투 화면 렌더링"""
    console.clear()
    console.print(Panel(f" ⏱ {turn}턴  │  💰 {player.gold}G  │  🏰 {player.current_floor}층", box=box.HORIZONTALS, style="dim white"))
    
    # 적 정보
    m_table = Table.grid(padding=(0, 1))
    m_table.add_column(width=30); m_table.add_column()
    m_table.add_row(f"[bold red]👾 {monster['name']}[/bold red] (SPD: {monster.get('spd', 5)})", 
                   f"{_hp_bar(monster['current_hp'], monster['hp'])} [white]{monster['current_hp']}/{monster['hp']}[/white]")
    
    m_status = " ".join([f"[bold red]{k.upper()}[/bold red]" for k, v in monster.get('statuses', {}).items() if v > 0])
    if m_status: m_table.add_row("", f"상태: {m_status}")
    console.print(Panel(m_table, title="[red]ENEMY[/red]", box=box.ROUNDED, style="red"))

    # 아군 정보
    p_table = Table.grid(padding=(0, 2))
    p_table.add_column(width=12); p_table.add_column(width=15); p_table.add_column(); p_table.add_column()
    
    for i, char in enumerate(player.party):
        mark = "[bold green]▶ 전방[/bold green]" if i == player.active_index else "[dim]  후방[/dim]"
        c_status = " ".join([f"[bold cyan]{k.upper()}[/bold cyan]" for k, v in char.get('statuses', {}).items() if v > 0])
        p_table.add_row(
            mark, 
            f"[bold]{char['name']}[/bold]\n[dim]{c_status}[/dim]", 
            f"{_hp_bar(char['current_hp'], char['hp'])} {char['current_hp']}/{char['hp']}", 
            f"⚡ [cyan]{char['current_energy']}/{char['mp']}[/cyan]"
        )
    console.print(Panel(p_table, title="[green]PARTY[/green]", box=box.ROUNDED, style="green"))

# ── 전투 로직 ──

def run_combat(player, monster):
    turn = 1
    player.init_combat_decks()
    _init_statuses(monster)

    while True:
        active = player.active_char
        player.apply_natural_regen()  # 유물 보너스가 포함된 마나 회복
        player.draw_cards(active, 4)  # 매 턴 4장 드로우

        # 1. 적의 행동 미리 결정 (속공 여부 판단용)
        pattern = monster.get('pattern', ['normal'])
        current_action = pattern[turn % len(pattern)]
        
        # 2. 우선 순위(선공) 결정
        monster_first = False
        if current_action == "quick":
            monster_first = True
            priority_msg = "[bold yellow]⚡ 경고! 적이 속공 기습을 준비합니다![/bold yellow]"
        elif monster.get('spd', 5) > active.get('spd', 10):
            monster_first = True
            priority_msg = f"[bold red]💨 적이 당신보다 빠릅니다! (적:{monster['spd']} vs 나:{active['spd']})[/bold red]"
        else:
            priority_msg = f"[bold green]✨ 당신이 더 빠릅니다! (나:{active['spd']} vs 적:{monster['spd']})[/bold green]"

        # 3. 턴 실행 루프
        if monster_first:
            draw_combat_screen(player, monster, turn)
            console.print(f"  {priority_msg}")
            _monster_turn_logic(monster, active, player, current_action)
            if active['current_hp'] <= 0: return False # 플레이어 패배
            
            if not _player_turn_logic(player, monster, active, turn): return True # 플레이어 승리
        else:
            draw_combat_screen(player, monster, turn)
            console.print(f"  {priority_msg}")
            if not _player_turn_logic(player, monster, active, turn): return True # 플레이어 승리
            
            _monster_turn_logic(monster, active, player, current_action)
            if active['current_hp'] <= 0: return False # 플레이어 패배

        # 4. 상태이상 갱신 및 턴 종료
        process_turn_statuses(active)
        process_turn_statuses(monster)
        turn += 1
        time.sleep(1)

def _player_turn_logic(player, monster, active, turn):
    """플레이어 행동 단계. 적이 죽으면 False를 반환하여 전투 종료 알림."""
    player_acted = False
    while not player_acted:
        draw_combat_screen(player, monster, turn)
        console.print("\n  [bold cyan]1.[/bold cyan] 평타   [bold cyan]2.[/bold cyan] 덱 사용   [bold cyan]3.[/bold cyan] 스왑\n")
        cmd = console.input("  선택: ").strip()

        if cmd == '1':
            dmg = max(1, get_effective_stat(active, 'atk') - get_effective_stat(monster, 'defense'))
            monster['current_hp'] -= dmg
            # 평타 시 파티 전원 EN 1 추가 회복 (전략적 요소)
            for c in player.party:
                c['current_energy'] = min(c['mp'], c['current_energy'] + 1)
            console.print(f"\n  [bold red]⚔  평타! {monster['name']}에게 {dmg} 피해! (파티 EN +1)[/bold red]")
            player_acted = True
            time.sleep(1)
        
        elif cmd == '2':
            if not _handle_card_use(player, monster, active):
                continue # 카드 사용 취소 시 다시 선택
            player_acted = True
            
        elif cmd == '3':
            player.swap()
            active = player.active_char
            player.draw_cards(active, 4)
            # 스왑은 턴을 소모하지 않거나, 소모하게 할 수 있음 (여기선 소모하게 설정)
            console.print(f"  [cyan]{active['name']}(으)로 교체되었습니다![/cyan]")
            player_acted = True
            time.sleep(0.8)

    if monster['current_hp'] <= 0:
        _victory_sequence(player, monster)
        return False
    return True

def _handle_card_use(player, monster, active):
    """카드 사용 인터페이스"""
    console.print("\n  [cyan]🃏 현재 손에 있는 패 (Hand)[/cyan]")
    for i, c_name in enumerate(active['hand'], 1):
        card = assets.CARDS.get(c_name, {})
        console.print(f"    {i}. [bold]{c_name}[/bold] (EN:{card['cost']}) - [dim]{card['description']}[/dim]")
    console.print("    0. 뒤로가기")
    
    try:
        idx = int(console.input("\n  사용할 카드 번호: ")) - 1
        if idx == -1: return False
        
        card_name = active['hand'][idx]
        card = assets.CARDS[card_name]
        
        if active['current_energy'] < card['cost']:
            console.print("  [red]❌ 에너지가 부족합니다![/red]")
            time.sleep(0.8)
            return False
        
        # 에너지 소모 및 카드 사용
        active['current_energy'] -= card['cost']
        active['discard_pile'].append(active['hand'].pop(idx))
        _execute_card_effects(card, active, player, monster)
        time.sleep(1.2)
        return True
    except:
        return False

def _execute_card_effects(card, active, player, monster):
    """카드 효과 실제 적용"""
    console.print(f"\n  [bold cyan]🃏 '{card['name']}' 발동![/bold cyan]")
    effect = card.get('effect')
    
    # 1. 회복 처리
    if card.get('heal', 0) > 0:
        heal_amt = card['heal']
        if card['target'] == 'ally':
            console.print("  누구를 치료하시겠습니까? 1.전사  2.마법사")
            try:
                t_idx = int(console.input("  대상: ")) - 1
                target = player.party[t_idx]
            except: target = active
            target['current_hp'] = min(target['hp'], target['current_hp'] + heal_amt)
            console.print(f"  [green]❤️ {target['name']}의 체력 {heal_amt} 회복![/green]")

    # 2. 버프 처리
    if effect == 'atk_up':
        for c in player.party:
            _init_statuses(c); c['statuses']['atk_up'] = 3
        console.print("  [yellow]💪 파티 전체의 공격력이 상승했습니다! (3턴)[/yellow]")
    elif effect == 'def_up':
        _init_statuses(active); active['statuses']['def_up'] = 3
        console.print(f"  [blue]🛡️ {active['name']}의 방어력이 상승했습니다! (3턴)[/blue]")

    # 3. 공격 처리
    if card.get('damage_mult', 0) > 0:
        base_atk = get_effective_stat(active, 'atk')
        dmg = max(1, int(base_atk * card['damage_mult']) - get_effective_stat(monster, 'defense'))
        monster['current_hp'] -= dmg
        console.print(f"  [bold red]⚔️ {monster['name']}에게 {dmg}의 강력한 피해![/bold red]")

        if effect == 'burn':
            _init_statuses(monster); monster['statuses']['burn'] = 3
            console.print(f"  [red]🔥 {monster['name']}에게 화상을 입혔습니다![/red]")
        elif effect == 'stun':
            _init_statuses(monster); monster['statuses']['stun'] = 1
            console.print(f"  [bold yellow]⚡ {monster['name']}이 기절했습니다![/bold yellow]")

def _monster_turn_logic(monster, active, player, action):
    """몬스터 공격 단계"""
    if monster['statuses'].get('stun', 0) > 0:
        console.print(f"\n  [bold yellow]⚡ {monster['name']}은(는) 기절하여 움직이지 못합니다![/bold yellow]")
        return

    base_dmg = monster['atk']
    
    if action == "quick":
        dmg = max(1, int(base_dmg * 0.8) - get_effective_stat(active, 'defense'))
        console.print(f"\n  [bold yellow]💥 속공! {monster['name']}이 번개처럼 달려듭니다![/bold yellow]")
        active['current_hp'] -= dmg
    elif action == "power":
        dmg = max(1, int(base_dmg * 1.5) - get_effective_stat(active, 'defense'))
        console.print(f"\n  [bold red]📢 {monster['name']}의 강력한 강타![/bold red]")
        active['current_hp'] -= dmg
    elif action == "fire_aoe" or action == "aoe":
        console.print(f"\n  [bold red]🔥 {monster['name']}의 광역 공격![/bold red]")
        for c in player.party:
            dmg = max(1, int(base_dmg * 1.1) - get_effective_stat(c, 'defense'))
            c['current_hp'] -= dmg
            console.print(f"    {c['name']}에게 {dmg} 피해!")
    else:
        dmg = max(1, base_dmg - get_effective_stat(active, 'defense'))
        console.print(f"\n  [bold red]👾 {monster['name']}의 공격![/bold red]")
        active['current_hp'] -= dmg

    console.print(f"  [red]{active['name']}에게 {dmg} 피해![/red]")
    time.sleep(1.2)

def _victory_sequence(player, monster):
    """전투 승리 및 카드 보상"""
    console.clear()
    gold = monster.get('reward_gold', 20)
    player.gold += gold
    console.print(Panel(f"[bold green]🎉 승리! {monster['name']}을(를) 물리쳤습니다![/bold green]\n💰 전리품: {gold}G 획득", box=box.DOUBLE))
    time.sleep(1.5)
    _card_reward_event(player)

def _card_reward_event(player):
    """직업 전용 카드 보상 시스템"""
    char = player.active_char
    # 직업 전용 카드 필터링
    class_cards = [k for k, v in assets.CARDS.items() if v['class'] == char['name']]
    choices = random.sample(class_cards, min(3, len(class_cards)))
    
    console.print(f"\n[bold yellow]🎁 새로운 기술을 발견했습니다! ({char['name']})[/bold yellow]\n")
    for i, c_name in enumerate(choices, 1):
        card = assets.CARDS[c_name]
        console.print(f"  {i}. [cyan]{card['name']}[/] (EN:{card['cost']}) - {card['description']}")
    console.print("  0. 스킵")
    
    while True:
        cmd = console.input(f"\n번호 선택: ")
        if cmd == '0': break
        if cmd in [str(j) for j in range(1, len(choices)+1)]:
            new_card = choices[int(cmd)-1]
            # 15장 제한 압축 로직
            if len(char['deck']) >= 15:
                console.print("\n[red]⚠️ 덱이 꽉 찼습니다 (최대 15장). 버릴 카드를 선택하세요:[/red]")
                for idx, name in enumerate(char['deck'], 1):
                    console.print(f"  {idx}. {name}")
                try:
                    drop = int(console.input("번호: ")) - 1
                    char['deck'].pop(drop)
                except: continue
            
            char['deck'].append(new_card)
            console.print(f"[bold green]✨ '{new_card}' 카드가 덱에 추가되었습니다![/bold green]")
            break
    time.sleep(1)