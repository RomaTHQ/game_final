from kivy.app import App
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.utils import hex_colormap, colormap
from kivy.animation import Animation
from kivy.metrics import sp, dp
from kivy.uix.image import Image
from kivy import platform
from kivy.properties import NumericProperty
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
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

    # КЛІК!
    def on_touch_down(self, touch):
        # Клік не обробляється, якщо не потрпаляє в рибу
        # або анімація зараз програється або заблокована взаємодія
        if not self.collide_point(*touch.pos) or self.anim_play or self.interaction_block:
            return

        if not self.anim_play and not self.interaction_block:
            self.hp_current -= 1
            self.GAME_SCREEN.score += self.points_per_click  # Добавляем очки в зависимости от рыбки

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

    def on_pre_enter(self, *args):
        self.score = 0

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

    def build(self):
        sm = ScreenManager()
        sm.add_widget(Menu(name="menu"))
        sm.add_widget(Game(name="game"))
        sm.add_widget(Settings(name="settings"))

        return sm


if platform != 'android':
    Window.size = (450, 900)

app = ClickerApp()
app.run()