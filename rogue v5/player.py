# player.py
import assets
import copy
import random
from collections import Counter
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

class Player:
    def __init__(self):
        self.party = [assets.get_class("전사"), assets.get_class("마법사")]
        self.relics = []

        for char in self.party:
            char['current_hp'] = char['hp']
            char['current_energy'] = 0
            char['draw_pile'] = []
            char['discard_pile'] = []
            char['hand'] = []

        self.active_index = 0
        self.gold = 100
        self.current_floor = 1

    @property
    def active_char(self):
        return self.party[self.active_index]

    def swap(self):
        self.active_index = 1 - self.active_index
        console.print(f"\n[cyan]🔄 캐릭터 교체! 현재 전방: [bold]{self.active_char['name']}[/bold][/cyan]")

    def init_combat_decks(self):
        bonus = sum(r.get('effect', {}).get('bonus_energy', 0) for r in self.relics)
        for char in self.party:
            char['draw_pile'] = char['deck'][:]
            random.shuffle(char['draw_pile'])
            char['discard_pile'] = []
            char['hand'] = []
            char['statuses'] = {}            # 이전 전투 상태이상 초기화
            char['current_energy'] = char['mp'] + bonus

    def draw_cards(self, char, count=4):
        char['discard_pile'].extend(char['hand'])
        char['hand'] = []

        for _ in range(count):
            if not char['draw_pile']:
                if not char['discard_pile']:
                    break  # 드로우 파일 + 버린패 모두 소진 → 더 이상 뽑을 카드 없음
                # 버린패를 섞어서 드로우 파일로 재활용
                char['draw_pile'] = char['discard_pile'][:]
                random.shuffle(char['draw_pile'])
                char['discard_pile'] = []
            char['hand'].append(char['draw_pile'].pop())

    def draw_cards_add(self, char, count):
        """현재 손패를 유지한 채로 카드를 추가 드로우합니다."""
        drawn = 0
        for _ in range(count):
            if not char['draw_pile']:
                if not char['discard_pile']:
                    break
                char['draw_pile'] = char['discard_pile'][:]
                random.shuffle(char['draw_pile'])
                char['discard_pile'] = []
            char['hand'].append(char['draw_pile'].pop())
            drawn += 1
        return drawn

    def reset_energy(self):
        """전방 캐릭터는 매 턴 에너지를 mp로 완전 리셋합니다.
        후방 캐릭터는 매 턴 +1씩 충전하며, mp*2까지 과다충전 가능합니다.
        스왑으로 후방 캐릭터를 꺼낼수록 더 강한 버스트를 낼 수 있습니다."""
        bonus = sum(r.get('effect', {}).get('bonus_energy', 0) for r in self.relics)
        front = self.active_char
        back  = self.party[1 - self.active_index]

        # 전방: 완전 리셋
        front['current_energy'] = front['mp'] + bonus

        # 후방: +1 충전 (mp*2 상한 — 과다충전)
        overcharge_cap = (back['mp'] + bonus) * 2
        back['current_energy'] = min(overcharge_cap, back['current_energy'] + 1)

    def heal_party(self, amount):
        for char in self.party:
            char['current_hp'] = min(char['hp'], char['current_hp'] + amount)

    def add_relic(self, relic):
        """유물 추가. 슬롯(최대 4개)이 꽉 찼으면 버릴 유물을 선택합니다."""
        if len(self.relics) >= 4:
            console.print("\n[bold yellow]유물 슬롯이 가득 찼습니다 (최대 4개). 버릴 유물을 선택하세요:[/bold yellow]")
            for i, r in enumerate(self.relics, 1):
                console.print(f"  {i}. [magenta]{r['name']}[/magenta] — [dim]{r.get('desc', '')}[/dim]")
            console.print("  0. 획득 포기")

            while True:
                try:
                    choice = int(console.input("선택: ").strip())
                    if choice == 0:
                        console.print("[dim]획득을 포기했습니다.[/dim]")
                        return False
                    if 1 <= choice <= len(self.relics):
                        discarded = self.relics.pop(choice - 1)
                        console.print(f"[dim]{discarded['name']}을(를) 버렸습니다.[/dim]")
                        break
                except ValueError:
                    pass

        self.relics.append(relic)
        console.print(f"\n[bold yellow]유물 획득: {relic['name']}![/bold yellow]")

        # 동적 처리 키는 건너뜀 (reset_energy / 전투 시작 / 매 턴에서 처리)
        DYNAMIC_KEYS = ('bonus_energy', 'poison_start', 'hp_drain', 'duration_bonus', 'burn_start')
        effect = relic.get('effect', {})
        for key, val in effect.items():
            if key in DYNAMIC_KEYS:
                continue
            elif key == 'hp':
                for char in self.party:
                    char['hp'] += val
                    char['current_hp'] += val
            elif key in ('atk', 'spd', 'mp'):
                for char in self.party:
                    char[key] = char.get(key, 0) + val

        self._check_synthesis()
        return True

    def _check_synthesis(self):
        relic_names = [r['name'] for r in self.relics]

        for materials, result in assets.RELIC_SYNTHESIS.items():
            mat1, mat2 = materials
            if mat1 in relic_names and mat2 in relic_names:
                idx1 = next(i for i, r in enumerate(self.relics) if r['name'] == mat1)
                self.relics.pop(idx1)

                relic_names = [r['name'] for r in self.relics]
                idx2 = next(i for i, r in enumerate(self.relics) if r['name'] == mat2)
                self.relics.pop(idx2)

                self.relics.append(result)

                console.print(f"\n[bold yellow]✨ 유물 공명(Synthesis) 발생!![/bold yellow]")
                console.print(f"[bold white]{mat1} + {mat2} → [magenta]{result['name']}[/magenta] 합성 성공![/bold white]")

                # 합성 결과물 effect도 파티에 반영
                for key, val in result.get('effect', {}).items():
                    if key in ('bonus_energy', 'poison_start'):
                        continue
                    elif key == 'hp':
                        for char in self.party:
                            char['hp'] += val
                            char['current_hp'] += val
                    elif key in ('atk', 'spd', 'mp'):
                        for char in self.party:
                            char[key] = char.get(key, 0) + val

                self._check_synthesis()
                return  # 합성 후 재귀 호출이 있으므로 여기서 종료

    def show_status(self):
        table = Table(title="🛡️ 파티 현황", box=box.ROUNDED, show_header=True, header_style="bold magenta")
        table.add_column("위치", justify="center", width=10)
        table.add_column("직업", justify="center", width=12)
        table.add_column("HP", justify="center", width=15)
        table.add_column("ATK", justify="center", width=8)
        table.add_column("덱", justify="center", width=8)

        for i, c in enumerate(self.party):
            pos = "[bold green]▶ 전방[/bold green]" if i == self.active_index else "[dim]  후방[/dim]"
            hp_color = "red" if c['current_hp'] < c['hp'] * 0.3 else "white"
            table.add_row(
                pos,
                c['name'],
                f"[{hp_color}]{c['current_hp']}/{c['hp']}[/]",
                str(c['atk']),
                f"{len(c.get('deck', []))}장"
            )
        console.print(table)
        console.print(f"  [yellow]보유 골드: {self.gold}G[/yellow]   [dim]유물: {len(self.relics)}/4[/dim]")

    def show_detailed_status(self):
        console.print(Panel(f"[bold white]Floor {self.current_floor} - 탐험가 기록부[/bold white]", style="blue", box=box.DOUBLE))
        self.show_status()

        console.print("\n[bold yellow]🃏 캐릭터별 보유 카드 덱 (Deck List)[/bold yellow]")
        for c in self.party:
            card_counts = Counter(c.get('deck', []))
            console.print(f"\n [cyan]{c['name']}[/cyan] 덱 ({len(c.get('deck', []))}장):")
            for name, count in card_counts.items():
                card = assets.CARDS.get(name, {})
                count_str = f" [dim]x{count}[/dim]" if count > 1 else ""
                desc = card.get('description', '')
                console.print(f"   • [bold]{name}[/bold]{count_str} (EN:{card.get('cost', '?')}) [dim]{desc}[/dim]")

        console.print("\n[bold yellow]💍 보유 중인 유물 (Inventory)[/bold yellow]")
        if self.relics:
            for r in self.relics:
                desc = r.get('desc', '특별한 효과가 없습니다.')
                console.print(f" • [bold magenta]{r['name']}[/bold magenta]: [italic white]{desc}[/italic white]")
        else:
            console.print(" [dim]보유 중인 유물이 없습니다.[/dim]")

        console.print("\n[bold yellow]📖 상태이상 효과 안내[/bold yellow]")
        for key, info in assets.STATUS_INFO.items():
            console.print(f" • [bold cyan]{info['name']}[/bold cyan]: [dim]{info['desc']}[/dim]")

        console.input("\n[Enter]를 눌러 던전으로 돌아가기...")