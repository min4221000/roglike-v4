# world.py
import random
import assets
import time
import combat
import visuals
from rich.console import Console
from rich import box

console = Console()
last_shop_floor = -3 

def generate_floor_event(floor):
    global last_shop_floor
    if floor == 1: return "shop" # 1층 확정 상점
    if floor in [15, 30]: return "boss" 
    rand = random.random()
    if rand > 0.85 and (floor - last_shop_floor >= 3):
        last_shop_floor = floor
        return "shop"
    return "combat" if rand < 0.75 else "event"

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
    return combat.run_combat(player, monster)

def handle_shop(player, floor):
    visuals.clear_screen()
    stage = assets.get_stage_by_floor(floor)
    shop_relics = assets.get_stage_relics(stage, count=2)
    
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
        
        choice = input("\n선택: ")
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
                else: console.print("[red]골드가 부족합니다![/]")
            elif c_idx == idx:
                if player.gold >= 40:
                    player.gold -= 40
                    player.heal_party(40)
                    console.print("[bold green]❤️ 체력이 회복되었습니다![/]")
                else: console.print("[red]골드가 부족합니다![/]")
        except ValueError: pass
        time.sleep(1.2)
        visuals.clear_screen()

def handle_random_event(player, floor):
    visuals.clear_screen()
    event = assets.get_random_event()
    console.print(f"🌀 [bold cyan][사건 발생] {event['name']}[/bold cyan]")
    console.print(f"📜 {event['description']}\n")
    for i, opt in enumerate(event['choices'], 1):
        console.print(f"  {i}. {opt['text']}")
    
    while True:
        try:
            res = input("\n선택: ")
            idx = int(res) - 1
            if 0 <= idx < len(event['choices']):
                sel = event['choices'][idx]
                console.print(f"\n✨ {sel.get('result_text', '결과가 나타납니다.')}")
                _apply_effect(player, sel['effect'])
                break
        except ValueError: pass
    time.sleep(2)

def _apply_effect(player, effect):
    if 'party_hp' in effect:
        for c in player.party: c['current_hp'] = max(0, min(c['hp'], c['current_hp'] + effect['party_hp']))
    if 'party_atk' in effect:
        for c in player.party: c['atk'] += effect['party_atk']
    if 'gold' in effect:
        player.gold = max(0, player.gold + effect['gold'])