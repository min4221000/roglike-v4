# world.py
import random
import assets
import time
import combat
import visuals
from rich.console import Console
from rich import box

console = Console()
last_shop_floor = 1  # 1층 상점 이후 기준점

def generate_floor_event(floor):
    global last_shop_floor
    if floor == 1:
        return "shop"               # 시작 확정 상점
    if floor in [15, 30]:
        return "boss"
    if floor in [14, 16, 29]:      # 보스 전후 확정 상점
        last_shop_floor = floor
        return "shop"

    # 최소 3층 간격이 지났을 때만 상점 등장 가능 (20% 확률)
    gap = floor - last_shop_floor
    if gap >= 3 and random.random() < 0.23:
        last_shop_floor = floor
        return "shop"

    return "combat" if random.random() < 0.75 else "event"

def handle_combat(player, floor):
    if floor in [15, 30]:
        monster = assets.get_boss(floor)
    else:
        stage = assets.get_stage_by_floor(floor)
        m_names = assets.get_stage_monsters(stage)
        monster = assets.get_monster(random.choice(m_names), floor)

    monster['current_hp'] = monster['hp']
    console.print(f"\n[bold red]🌑 야생의 {monster['name']}이(가) 나타났다![/bold red]")
    time.sleep(1.2)

    result = combat.run_combat(player, monster)

    # [버그13 수정] 보스 처치 후 HP 30 회복
    if result and floor in [15, 30]:
        player.heal_party(30)
        console.print(f"\n[bold green]✨ 보스 처치 보상! 파티 전원 HP 30 회복![/bold green]")
        time.sleep(1.2)

    return result

def handle_shop(player, floor):
    visuals.clear_screen()
    stage = assets.get_stage_by_floor(floor)
    shop_relics = assets.get_stage_relics(stage, count=3)

    while True:
        console.print(f"🛒 [bold yellow][암시장 상점][/bold yellow] (보유: [yellow]{player.gold}G[/yellow])\n")

        idx = 1
        for r in shop_relics:
            price = r.get('price', 80)
            desc = r.get('desc', "효과가 비밀에 싸여있습니다.")
            console.print(f"  {idx}. [bold magenta]💍 {r['name']}[/bold magenta] ([yellow]{price}G[/yellow])")
            console.print(f"     [dim italic]ㄴ 효과: {desc}[/dim italic]")
            idx += 1

        console.print(f"  {idx}. ❤️ [bold red]파티 전원 HP 40 회복[/bold red] (40G)")
        console.print("  0. 떠나기")

        choice = console.input("\n선택: ").strip()
        if choice == '0': break
        try:
            c_idx = int(choice)
            if 1 <= c_idx < idx:
                selected = shop_relics[c_idx - 1]
                if player.gold >= selected['price']:
                    if player.add_relic(selected):
                        player.gold -= selected['price']
                        shop_relics.pop(c_idx - 1)
                        console.print(f"[bold green]✔ {selected['name']} 구매 완료![/]")
                else:
                    console.print("[red]골드가 부족합니다![/]")
            elif c_idx == idx:
                if player.gold >= 40:
                    player.gold -= 40
                    player.heal_party(40)
                    console.print("[bold green]❤️ 체력이 회복되었습니다![/]")
                else:
                    console.print("[red]골드가 부족합니다![/]")
        except ValueError:
            pass
        time.sleep(1.2)
        visuals.clear_screen()

def handle_random_event(player, floor):
    visuals.clear_screen()
    event = assets.get_random_event()
    console.print(f"🌀 [bold cyan][사건 발생] {event['name']}[/bold cyan]  [yellow]{player.gold}G[/yellow]")
    console.print(f"📜 {event['description']}\n")
    for i, opt in enumerate(event['choices'], 1):
        console.print(f"  {i}. {opt['text']}")

    while True:
        try:
            res = console.input("\n선택: ").strip()
            idx = int(res) - 1
            if 0 <= idx < len(event['choices']):
                sel = event['choices'][idx]
                console.print(f"\n✨ {sel.get('result_text', '결과가 나타납니다.')}")
                _apply_effect(player, sel['effect'])
                break
        except ValueError:
            pass
    time.sleep(2)

def _apply_effect(player, effect):
    # 골드 변동 (chance 적용)
    if 'gold' in effect:
        chance = effect.get('chance', 1.0)
        if random.random() < chance:
            player.gold = max(0, player.gold + effect['gold'])

    # HP 변동 (chance 적용)
    if 'party_hp' in effect:
        chance = effect.get('chance', 1.0)
        if random.random() < chance:
            hp_val = effect['party_hp']
            for c in player.party:
                c['current_hp'] = max(0, min(c['hp'], c['current_hp'] + hp_val))
            if hp_val < 0:
                console.print(f"[bold red]함정 발동! 파티 전원 HP {hp_val}![/bold red]")
        else:
            console.print("[green]다행히 함정은 없었습니다.[/green]")

    # 공격력 영구 변동
    if 'party_atk' in effect:
        val = effect['party_atk']
        for c in player.party:
            c['atk'] = max(1, c['atk'] + val)
        sign = f"+{val}" if val > 0 else str(val)
        console.print(f"[yellow]파티 ATK {sign} (영구)[/yellow]")

    # 골드 도박: 배팅 후 win_chance 확률로 win_mult 배 획득, 실패 시 bet 손실
    if 'gamble' in effect:
        g   = effect['gamble']
        bet = g.get('bet', 0)
        if player.gold < bet:
            console.print("[red]골드가 부족합니다![/red]")
        else:
            player.gold -= bet
            if random.random() < g.get('win_chance', 0.5):
                # 일반 골드 당첨
                win_gold = int(bet * g.get('win_mult', 2))
                player.gold += win_gold
                console.print(f"[bold green]당첨! +{win_gold}G 획득! (보유: {player.gold}G)[/bold green]")
                # 보너스 스탯 당첨 (어둠의 속삭임 등)
                if 'win_bonus' in g:
                    _apply_effect(player, g['win_bonus'])
            else:
                console.print(f"[bold red]꽝! {bet}G를 잃었습니다. (보유: {player.gold}G)[/bold red]")

    # 스탯 도박: win_chance 확률로 win_effect, 실패 시 lose_effect 적용
    if 'gamble_stat' in effect:
        g = effect['gamble_stat']
        if random.random() < g.get('win_chance', 0.5):
            console.print("[bold green]행운이 따릅니다![/bold green]")
            _apply_effect(player, g.get('win_effect', {}))
        else:
            console.print("[bold red]불운이 찾아왔습니다![/bold red]")
            _apply_effect(player, g.get('lose_effect', {}))

    # 공용 카드 지급
    if 'give_card' in effect:
        card_name = effect['give_card']
        card = assets.CARDS.get(card_name)
        if not card:
            return
        console.print(f"\n[bold yellow]'{card_name}' 카드를 획득했습니다![/bold yellow]")
        console.print(f"[dim]{card['description']}[/dim]")
        console.print("  누구의 덱에 추가할까요?")
        for i, c in enumerate(player.party, 1):
            console.print(f"  {i}. {c['name']} (현재 {len(c['deck'])}장)")
        try:
            t_idx = int(console.input("선택: ").strip()) - 1
            target = player.party[t_idx]
        except (ValueError, IndexError):
            target = player.party[0]

        if len(target['deck']) >= 15:
            console.print(f"\n[red]{target['name']}의 덱이 꽉 찼습니다. 버릴 카드를 선택하세요:[/red]")
            for i, name in enumerate(target['deck'], 1):
                console.print(f"  {i}. {name}")
            try:
                drop = int(console.input("번호: ").strip()) - 1
                target['deck'].pop(drop)
            except (ValueError, IndexError):
                pass

        target['deck'].append(card_name)
        console.print(f"[bold green]{target['name']}의 덱에 '{card_name}' 추가 완료![/bold green]")