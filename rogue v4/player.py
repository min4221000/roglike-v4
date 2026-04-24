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
        # [간소화] 직업 선택 삭제: 전사와 마법사 고정 파티
        self.party = [assets.get_class("전사"), assets.get_class("마법사")]
        self.relics = [] # 보유 유물 리스트 (최대 5개)
        
        # 파티원 상태 초기화
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
        """현재 전방에 있는 활성화된 캐릭터를 반환합니다."""
        return self.party[self.active_index]

    def swap(self):
        """캐릭터 위치를 교체(태그)합니다."""
        self.active_index = 1 - self.active_index
        console.print(f"\n[cyan]🔄 캐릭터 교체! 현재 전방: [bold]{self.active_char['name']}[/bold][/cyan]")

    def init_combat_decks(self):
        """전투 시작 시 덱을 섞고 초기화합니다."""
        for char in self.party:
            char['draw_pile'] = char['deck'][:]
            random.shuffle(char['draw_pile'])
            char['discard_pile'] = []
            char['hand'] = []

    def draw_cards(self, char, count=4):
        """카드를 드로우합니다."""
        char['discard_pile'].extend(char['hand'])
        char['hand'] = []
        
        for _ in range(count):
            if not char['draw_pile']:
                if not char['discard_pile']: break
                char['draw_pile'] = char['discard_pile'][:]
                random.shuffle(char['draw_pile'])
                char['discard_pile'] = []
            
            if char['draw_pile']:
                char['hand'].append(char['draw_pile'].pop())

    def apply_natural_regen(self):
        """매 턴 기력(EN)을 회복합니다. (유물 효과 확장 가능)"""
        for char in self.party:
            # 기본 회복량 1 (마나파편 등 유물 효과는 combat.py나 여기서 합산)
            char['current_energy'] = min(10, char['current_energy'] + 1)

    def heal_party(self, amount):
        """파티원 전체의 HP를 회복시킵니다."""
        for char in self.party:
            char['current_hp'] = min(char['hp'], char['current_hp'] + amount)

    def add_relic(self, relic):
        """유물을 인벤토리에 추가하고 자동 합성을 체크합니다."""
        if len(self.relics) < 5:
            self.relics.append(relic)
            console.print(f"\n[bold yellow]💍 유물 획득: {relic['name']}![/bold yellow]")
            self._check_synthesis() # 획득 즉시 합성 여부 확인
            return True
        else:
            console.print("\n[red]⚠️ 유물 슬롯이 가득 찼습니다! (최대 5개)[/red]")
            return False

    def _check_synthesis(self):
        """보유 중인 유물 중 조합 가능한 쌍이 있는지 확인하고 자동 합성합니다."""
        relic_names = [r['name'] for r in self.relics]
        
        # assets.py의 RELIC_SYNTHESIS (튜플 키) 순회
        for materials, result in assets.RELIC_SYNTHESIS.items():
            mat1, mat2 = materials
            if mat1 in relic_names and mat2 in relic_names:
                # 1. 재료 제거 (순차적으로)
                idx1 = next(i for i, r in enumerate(self.relics) if r['name'] == mat1)
                self.relics.pop(idx1)
                
                # 하나가 빠졌으니 이름을 다시 리스트화하여 두 번째 재료 찾기
                relic_names = [r['name'] for r in self.relics]
                idx2 = next(i for i, r in enumerate(self.relics) if r['name'] == mat2)
                self.relics.pop(idx2)
                
                # 2. 합성 결과물 추가
                self.relics.append(result)
                
                console.print(f"\n[bold yellow]✨ 유물 공명(Synthesis) 발생!![/bold yellow]")
                console.print(f"[bold white]{mat1} + {mat2} -> [magenta]{result['name']}[/magenta] 합성에 성공했습니다![/bold white]")
                
                # 3. 추가 합성이 있을 수 있으므로 재귀 호출
                self._check_synthesis()
                break

    def show_status(self):
        """메인 화면에 표시될 파티 요약 정보를 출력합니다."""
        table = Table(title="🛡️ 파티 현황", box=box.ROUNDED, show_header=True, header_style="bold magenta")
        table.add_column("위치", justify="center", width=10)
        table.add_column("직업", justify="center", width=12)
        table.add_column("HP", justify="center", width=15)
        table.add_column("ATK", justify="center", width=8)
        table.add_column("DEF", justify="center", width=8)
        table.add_column("덱", justify="center", width=8)

        for i, c in enumerate(self.party):
            pos = "[bold green]▶ 전방[/bold green]" if i == self.active_index else "[dim]  후방[/dim]"
            hp_color = "red" if c['current_hp'] < c['hp'] * 0.3 else "white"
            
            table.add_row(
                pos, 
                c['name'], 
                f"[{hp_color}]{c['current_hp']}/{c['hp']}[/]", 
                str(c['atk']), 
                str(c['defense']), 
                f"{len(c.get('deck', []))}장"
            )
        console.print(table)

    def show_detailed_status(self):
        """[I] 상세 정보 창: 덱 목록과 유물 설명을 출력합니다."""
        visuals_header = Panel(f"[bold white]Floor {self.current_floor} - 탐험가 기록부[/bold white]", style="blue", box=box.DOUBLE)
        console.print(visuals_header)
        
        self.show_status() # 기본 표 포함
        
        # 1. 캐릭터별 덱 정보 출력
        console.print("\n[bold yellow]🃏 캐릭터별 보유 카드 덱 (Deck List)[/bold yellow]")
        for c in self.party:
            card_counts = Counter(c.get('deck', []))
            deck_display = [f"{name} [dim]x{count}[/dim]" if count > 1 else name for name, count in card_counts.items()]
            console.print(f" • [cyan]{c['name']}[/]: {" | ".join(deck_display)}")
        
        # 2. 보유 유물 및 상세 설명 출력
        console.print("\n[bold yellow]💍 보유 중인 유물 (Inventory)[/bold yellow]")
        if self.relics:
            for r in self.relics:
                # 설명 키값은 desc를 우선 참조
                desc = r.get('desc', r.get('effect_desc', "특별한 효과가 없습니다."))
                console.print(f" • [bold magenta]{r['name']}[/bold magenta]: [italic white]{desc}[/italic white]")
        else:
            console.print(" [dim]보유 중인 유물이 없습니다.[/dim]")
            
        input("\n[Enter]를 눌러 던전으로 돌아가기...")