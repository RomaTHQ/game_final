from kivy.app import App
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.utils import hex_colormap, colormap
from kivy.animation import Animation
from kivy.metrics import sp, dp
from kivy.uix.image import Image
from kivy import platform
from kivy.properties import NumericProperty, StringProperty
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
import random


class Menu(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

    # Перехід до екрана гри
    def go_game(self, *args):
        self.manager.current = "game"
        self.manager.transition.direction = "left"

    # Перехід до екрана налаштувань
    def go_settings(self, *args):
        self.manager.current = "settings"
        self.manager.transition.direction = "up"

    # Вихід з програми
    def exit_app(self, *args):
        app.stop()


class Settings(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # Повернення до меню
    def go_menu(self, *args):
        self.manager.current = "menu"
        self.manager.transition.direction = "down"


# Виджет одного улучшения в магазине
class ShopUpgrade(BoxLayout):
    upgrade_name = StringProperty("")
    upgrade_level = NumericProperty(0)
    upgrade_cost = NumericProperty(0)
    upgrade_key = StringProperty("")

    def __init__(self, upgrade_key, **kwargs):
        super().__init__(**kwargs)
        self.upgrade_key = upgrade_key
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(80)
        self.padding = dp(5)
        self.spacing = dp(3)

        upgrade_data = app.UPGRADES[upgrade_key]
        self.upgrade_name = upgrade_data['name']
        self.upgrade_level = upgrade_data['level']
        self.upgrade_cost = upgrade_data['base_cost'] * (upgrade_data['level'] + 1)

        # Название улучшения
        name_label = Label(
            text=self.upgrade_name,
            size_hint_y=0.3,
            font_size=sp(12),
            bold=True
        )

        # Уровень и бонус
        level_text = f"Ур. {self.upgrade_level} | +{upgrade_data['bonus_per_level'] * self.upgrade_level}"
        level_label = Label(
            text=level_text,
            size_hint_y=0.3,
            font_size=sp(10)
        )

        # Кнопка покупки
        self.buy_button = Button(
            text=f"Купить: {self.upgrade_cost}",
            size_hint_y=0.4,
            font_size=sp(11),
            background_color=(0.2, 0.6, 0.8, 1)
        )
        self.buy_button.bind(on_press=self.buy_upgrade)

        self.add_widget(name_label)
        self.add_widget(level_label)
        self.add_widget(self.buy_button)

    def buy_upgrade(self, instance):
        game_screen = app.root.get_screen('game')

        # Проверяем, достаточно ли очков
        if game_screen.score >= self.upgrade_cost:
            game_screen.score -= self.upgrade_cost
            app.UPGRADES[self.upgrade_key]['level'] += 1

            # Обновляем информацию в магазине
            game_screen.ids.shop_panel.update_shop()


# Панель магазина
class ShopPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint = (None, 1)
        self.width = dp(180)
        self.pos_hint = {'right': 1}
        self.padding = dp(10)
        self.spacing = dp(10)
        self.opacity = 0  # Скрыт по умолчанию

        # Заголовок магазина
        header_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(40)
        )

        title = Label(
            text="МАГАЗИН",
            font_size=sp(16),
            bold=True,
            color=(1, 1, 0, 1)
        )

        # Кнопка закрытия
        close_btn = Button(
            text="X",
            size_hint=(None, 1),
            width=dp(40),
            font_size=sp(18),
            background_color=(0.8, 0.2, 0.2, 1)
        )
        close_btn.bind(on_press=self.toggle_shop)

        header_layout.add_widget(title)
        header_layout.add_widget(close_btn)

        self.add_widget(header_layout)

        # Контейнер для улучшений
        self.upgrades_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(10)
        )
        self.upgrades_container.bind(minimum_height=self.upgrades_container.setter('height'))

        self.add_widget(self.upgrades_container)

        self.update_shop()

    def toggle_shop(self, *args):
        """Переключение видимости магазина"""
        if self.opacity == 0:
            # Показать магазин
            anim = Animation(opacity=1, x=Window.width - self.width, duration=0.3)
            anim.start(self)
        else:
            # Скрыть магазин
            anim = Animation(opacity=0, x=Window.width, duration=0.3)
            anim.start(self)

    def update_shop(self):
        self.upgrades_container.clear_widgets()

        # Создаем виджеты для каждого улучшения
        for upgrade_key in app.UPGRADES:
            upgrade_widget = ShopUpgrade(upgrade_key)
            self.upgrades_container.add_widget(upgrade_widget)

        self.upgrades_container.height = len(app.UPGRADES) * dp(90)


# Клас для обертання картинок; в класі, який спадковує потрібно дадати властивість angle
class RotatedImage(Image):
    ...


# КЛАС РИБИ: Обробка кліків, створення "нової" риби
class Fish(RotatedImage):
    # Властивість для забезпечення програвання однієї анімації в один проміжок часу
    anim_play = False
    interaction_block = True
    COEF_MULT = 1.5
    fish_current = None
    hp_current = None
    points_per_click = 1  # Очки за один клік
    angle = NumericProperty(0)

    click_music = SoundLoader.load('assets/audios/bubble01.mp3')
    defeate_music = SoundLoader.load('assets/audios/fish_def.ogg')

    def on_kv_post(self, base_widget):
        self.GAME_SCREEN = self.parent.parent.parent

        return super().on_kv_post(base_widget)

    def new_fish(self, *args):
        # Случайный выбор рыбки
        fish_keys = list(app.FISHES.keys())
        self.fish_current = random.choice(fish_keys)

        fish_data = app.FISHES[self.fish_current]
        self.source = fish_data['source']
        self.hp_current = fish_data['hp']
        self.points_per_click = fish_data['points']  # Получаем очки за клик

        self.swim()

    def swim(self):
        self.pos = (self.GAME_SCREEN.x - self.width, self.GAME_SCREEN.height / 2)
        self.opacity = 1
        swim = Animation(x=self.GAME_SCREEN.width / 2 - self.width / 2, duration=1)
        swim.start(self)

        swim.bind(on_complete=lambda w, a: setattr(self, "interaction_block", False))

    # Перемогли рибу :)
    def defeated(self):
        self.interaction_block = True
        # Анімація обертання
        anim = Animation(angle=self.angle + 360, d=1, t='in_cubic')

        # Запам'ятовуємо старі розмір і позицію для анімації зменшення
        old_size = self.size.copy()
        old_pos = self.pos.copy()
        # Новий розмір
        new_size = (self.size[0] * self.COEF_MULT * 3, self.size[1] * self.COEF_MULT * 3)
        # Нова позиція риби при збільшенні
        new_pos = (self.pos[0] - (new_size[0] - self.size[0]) / 2, self.pos[1] - (new_size[0] - self.size[1]) / 2)
        # АНІМАЦІЯ ЗБІЛЬШЕННЯ/ЗМЕНШЕННЯ
        anim &= Animation(size=(new_size), t='in_out_bounce') + Animation(size=(old_size), duration=0)
        anim &= Animation(pos=(new_pos), t='in_out_bounce') + Animation(pos=(old_pos), duration=0)

        anim &= Animation(opacity=0)
        anim.start(self)

        self.defeate_music.play()

    def get_total_click_bonus(self):
        """Получить суммарный бонус от всех улучшений"""
        total_bonus = 0
        for upgrade_key, upgrade_data in app.UPGRADES.items():
            total_bonus += upgrade_data['level'] * upgrade_data['bonus_per_level']
        return total_bonus

    # КЛІК!
    def on_touch_down(self, touch):
        # Клік не обробляється, якщо не потрпаляє в рибу
        # або анімація зараз програється або заблокована взаємодія
        if not self.collide_point(*touch.pos) or self.anim_play or self.interaction_block:
            return

        if not self.anim_play and not self.interaction_block:
            self.hp_current -= 1

            # Считаем очки с учетом улучшений
            click_points = self.points_per_click + self.get_total_click_bonus()
            self.GAME_SCREEN.score += click_points

            self.click_music.play()
            # Клік призвів до змеьшення hp риби
            if self.hp_current > 0:
                # Запам'ятовуємо старі розмір і позицію для анімації зменшення
                old_size = self.size.copy()
                old_pos = self.pos.copy()

                # Новий розмір
                new_size = (self.size[0] * self.COEF_MULT, self.size[1] * self.COEF_MULT)
                # Нова позиція риби при збільшенні
                new_pos = (self.pos[0] - (new_size[0] - self.size[0]) / 2,
                           self.pos[1] - (new_size[0] - self.size[1]) / 2)

                # АНІМАЦІЯ ЗБІЛЬШЕННЯ/ЗМЕНШЕННЯ
                zoom_anim = Animation(size=(new_size), duration=0.05) + Animation(size=(old_size), duration=0.05)
                zoom_anim &= Animation(pos=(new_pos), duration=0.05) + Animation(pos=(old_pos), duration=0.05)

                zoom_anim.start(self)
                self.anim_play = True

                zoom_anim.bind(on_complete=lambda *args: setattr(self, "anim_play", False))
            # Клік призвів до знищення риби
            else:
                self.defeated()

                # Запуск новой рыбки после 1.2 секунды
                Clock.schedule_once(self.new_fish, 1.2)

        return super().on_touch_down(touch)


class Game(Screen):
    score = NumericProperty(0)
    back_sound = SoundLoader.load('assets/audios/Black_Swan_part.mp3')
    back_sound.loop = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Создаем кнопку открытия магазина
        self.shop_button = Button(
            text="🛒",
            size_hint=(None, None),
            size=(dp(50), dp(50)),
            pos_hint={'right': 1, 'top': 1},
            font_size=sp(24),
            background_color=(0.2, 0.7, 0.3, 1)
        )
        self.shop_button.bind(on_press=self.toggle_shop)

    def on_kv_post(self, base_widget):
        # Добавляем кнопку магазина поверх всего
        self.add_widget(self.shop_button)
        return super().on_kv_post(base_widget)

    def toggle_shop(self, *args):
        """Открыть/закрыть магазин"""
        if hasattr(self.ids, 'shop_panel'):
            self.ids.shop_panel.toggle_shop()

    def on_pre_enter(self, *args):
        # Не сбрасываем счет при перезапуске, чтобы сохранить прогресс
        if not hasattr(self, 'game_started'):
            self.score = 0
            self.game_started = True

        return super().on_pre_enter(*args)

    def on_enter(self, *args):
        label_animation = (
                Animation(y=(self.height - self.ids.level_title.height) / 2 + dp(100), duration=1)
                + Animation(opacity=1, duration=1)
                + Animation(y=self.height, duration=1)
        )
        # Плавне зникнення напису при спливанні вгору
        label_animation &= Animation(opacity=1, duration=2) + Animation(opacity=0, duration=1)

        label_animation.start(self.ids.level_title)
        label_animation.bind(on_complete=self.start_game)

        self.back_sound.play()

        return super().on_enter(*args)

    def start_game(self, animation, widget):
        self.ids.fish.new_fish()

    def go_home(self):
        fish_disapear_anim = Animation(opacity=0, duration=0.1)
        fish_disapear_anim.start(self.ids.fish)

        self.back_sound.stop()

        self.manager.current = "menu"
        self.manager.transition.direction = "right"


class ClickerApp(App):
    FISHES = {
        'fish1':
            {'source': 'assets/images/fish_01.png', 'hp': 10, 'points': 1},  # Первая рыбка - 1 очко за клик
        'fish2':
            {'source': 'assets/images/fish_02.png', 'hp': 20, 'points': 3}  # Вторая рыбка - 3 очка за клик
    }

    # Улучшения для магазина
    UPGRADES = {
        'power_click': {
            'name': 'Сила клика',
            'level': 0,
            'base_cost': 10,  # Базовая цена
            'bonus_per_level': 1  # Бонус за уровень
        },
        'mega_power': {
            'name': 'Мега сила',
            'level': 0,
            'base_cost': 50,
            'bonus_per_level': 5
        },
        'ultra_click': {
            'name': 'Ультра клик',
            'level': 0,
            'base_cost': 200,
            'bonus_per_level': 20
        }
    }

    def build(self):
        sm = ScreenManager()
        sm.add_widget(Menu(name="menu"))

        # Создаем игровой экран
        game_screen = Game(name="game")

        # Добавляем магазин в игровой экран через kv или код
        # Здесь нужно будет добавить ShopPanel в .kv файл или программно

        sm.add_widget(game_screen)
        sm.add_widget(Settings(name="settings"))

        return sm


if platform != 'android':
    Window.size = (450, 900)

app = ClickerApp()
app.run()