"""Offline workout diary for desktop and Android."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from kivy.config import Config
Config.set("graphics", "softinput_mode", "resize")

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from catalog import EXERCISES
from guide import GENERAL, GUIDE
from storage import WorkoutStore, parse_workout_date


def label(text: str, height: int = 36) -> Label:
    result = Label(text=text, size_hint_y=None, height=dp(height),
                   color=(0.98, 0.88, 0.56, 1), halign="center", valign="middle")
    def draw_label(*_):
        result.canvas.before.clear()
        x, y = result.pos
        w, h = result.size
        p = dp(4)
        with result.canvas.before:
            Color(0.08, 0.07, 0.05, 1)
            Rectangle(pos=(x + p, y), size=(max(0, w - 2*p), h))
            Rectangle(pos=(x, y + p), size=(w, max(0, h - 2*p)))
            Color(0.22, 0.19, 0.12, 1)
            Rectangle(pos=(x + p, y + p), size=(max(0, w - 2*p), max(0, h - 2*p)))
    result.bind(pos=draw_label, size=draw_label)
    draw_label()
    return result


class PixelTextInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(background_normal="", background_active="", background_color=(1, 1, 1, 1),
                         padding=(dp(12), dp(12), dp(12), dp(8)), **kwargs)
        self.bind(pos=self.draw_border, size=self.draw_border)
        self.draw_border()

    def draw_border(self, *_):
        self.canvas.after.clear()
        x, y = self.pos
        w, h = self.size
        p = dp(4)
        with self.canvas.after:
            Color(0.08, 0.07, 0.05, 1)
            Rectangle(pos=(x + p, y), size=(max(0, w - 2*p), p))
            Rectangle(pos=(x + p, y + h - p), size=(max(0, w - 2*p), p))
            Rectangle(pos=(x, y), size=(p, h))
            Rectangle(pos=(x + w - p, y), size=(p, h))


class PixelButton(Button):
    def __init__(self, **kwargs):
        super().__init__(background_normal="", background_down="", background_color=(0, 0, 0, 0),
                         color=(0.98, 0.88, 0.56, 1), **kwargs)
        self.bind(pos=self.draw_frame, size=self.draw_frame, state=self.draw_frame)
        self.draw_frame()

    def draw_frame(self, *_):
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        p = dp(4)
        with self.canvas.before:
            Color(0.08, 0.07, 0.05, 1)
            Rectangle(pos=(x + p, y), size=(max(0, w - 2*p), h))
            Rectangle(pos=(x, y + p), size=(w, max(0, h - 2*p)))
            Color(*( (0.34, 0.27, 0.12, 1) if self.state == "down" else (0.22, 0.19, 0.12, 1) ))
            Rectangle(pos=(x + p, y + p), size=(max(0, w - 2*p), max(0, h - 2*p)))
            Color(0.65, 0.50, 0.22, 1)
            Rectangle(pos=(x + 2*p, y + h - 2*p), size=(max(0, w - 4*p), p))


def button(text: str, callback, height: int = 48) -> Button:
    result = PixelButton(text=text, size_hint_y=None, height=dp(height))
    result.bind(on_release=callback)
    return result


def joined(*widgets):
    """Stack related controls without showing the background between them."""
    group = BoxLayout(orientation="vertical", size_hint_y=None, spacing=0)
    group.bind(minimum_height=group.setter("height"))
    for widget in widgets:
        group.add_widget(widget)
    return group


class WorkoutApp(App):
    title = "Дневник тренировок"

    def build(self):
        self.store = WorkoutStore(Path(self.user_data_dir) / "workouts.db")
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        root.bind(pos=self.draw_home, size=self.draw_home)
        self.root_layout = root
        self.tabs = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        self.tabs.add_widget(button("Меню", lambda *_: self.show_home()))
        self.tabs.add_widget(button("Запись", lambda *_: self.show_entry()))
        self.tabs.add_widget(button("История", lambda *_: self.show_history()))
        self.content = BoxLayout(orientation="vertical")
        root.add_widget(self.content)
        self.show_home()
        return root

    def show_home(self):
        if self.tabs.parent:
            self.root_layout.remove_widget(self.tabs)
        home = BoxLayout(orientation="vertical")
        for index, title in enumerate(("Дневник тренировок", "Спортивная библиотека", "Прогноз", "Анализ")):
            row = BoxLayout(padding=(dp(30), dp(12)))
            row.add_widget(button(title, lambda _btn, name=title: self.open_section(name), 64))
            home.add_widget(row)
        self.replace_content(home)

    def draw_home(self, widget, *_):
        widget.canvas.before.clear()
        with widget.canvas.before:
            for row in range(2):
                for col in range(10):
                    light = (col + row) % 2 == 0
                    Color(*( (0.48, 0.39, 0.18, 1) if light else (0.12, 0.11, 0.09, 1) ))
                    Rectangle(pos=(widget.x + col * widget.width / 10, widget.top - (row + 1) * widget.height / 2),
                              size=(widget.width / 10 + 1, widget.height / 2 + 1))

    def open_section(self, name):
        if name == "Дневник тренировок":
            self.root_layout.add_widget(self.tabs, index=1)
            self.show_entry()
        elif name == "Спортивная библиотека":
            self.show_library()
        else:
            body = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
            body.add_widget(Label(text=name + "\n\nРаздел появится позже", halign="center"))
            body.add_widget(button("В главное меню", lambda *_: self.show_home()))
            self.replace_content(body)

    def show_library(self):
        scroll = ScrollView()
        body = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        body.bind(minimum_height=body.setter("height"))
        body.add_widget(button("Главное меню", lambda *_: self.show_home()))
        group = button("Выберите группу", lambda *_: self.choose_value(group, "Группа мышц"))
        group.values = tuple(EXERCISES)
        exercise = button("Выберите упражнение", lambda *_: self.choose_value(exercise, "Упражнение"))
        exercise.values = ()
        body.add_widget(joined(label("Группа мышц"), group))
        body.add_widget(joined(label("Упражнение"), exercise))
        details = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        details.bind(minimum_height=details.setter("height"))
        body.add_widget(details)

        def paragraph(title, value):
            text = label(value)
            text.halign = "left"
            text.padding = (dp(12), dp(10))
            text.bind(width=lambda widget, width: setattr(widget, "text_size", (max(0, width - dp(24)), None)))
            text.bind(texture_size=lambda widget, size: setattr(widget, "height", max(dp(48), size[1] + dp(24))))
            details.add_widget(joined(label(title), text))

        def group_changed(_button, value):
            exercise.values = EXERCISES.get(value, ())
            exercise.text = "Выберите упражнение"
            details.clear_widgets()

        def exercise_changed(_button, value):
            details.clear_widgets()
            if value in GUIDE:
                muscles, technique, tip = GUIDE[value]
                paragraph("Какие мышцы работают", muscles)
                paragraph("Как выполнять", technique)
                paragraph("На что обратить внимание", tip)
                paragraph("Подходы и вес", GENERAL)

        group.bind(text=group_changed)
        exercise.bind(text=exercise_changed)
        scroll.add_widget(body)
        self.replace_content(scroll)

    def choose_value(self, target, title):
        if not target.values:
            self.show_message("Выбор упражнения", "Сначала выберите группу мышц")
            return
        body = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
        scroll = ScrollView()
        choices = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(5))
        choices.bind(minimum_height=choices.setter("height"))
        popup = Popup(title=title, content=body, size_hint=(0.92, 0.8))
        def select(value):
            target.text = value
            popup.dismiss()
        for value in target.values:
            choices.add_widget(button(value, lambda _btn, item=value: select(item), 52))
        scroll.add_widget(choices)
        body.add_widget(scroll)
        body.add_widget(button("Отмена", lambda *_: popup.dismiss()))
        popup.open()

    def follow_input(self, field, scroll):
        def on_focus(_field, focused):
            if focused:
                Clock.schedule_once(lambda _dt: scroll.scroll_to(field, padding=dp(24), animate=False), 0.35)
        field.bind(focus=on_focus)

    def on_stop(self):
        self.store.close()

    def show_message(self, title: str, message: str):
        body = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        body.add_widget(Label(text=message, halign="center"))
        close = button("Понятно", lambda *_: popup.dismiss())
        body.add_widget(close)
        popup = Popup(title=title, content=body, size_hint=(0.9, 0.45))
        popup.open()

    def replace_content(self, widget):
        self.content.clear_widgets()
        self.content.add_widget(widget)

    def build_entry(self):
        scroll = ScrollView()
        form = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))
        self.date_input = PixelTextInput(text=date.today().isoformat(), multiline=False,
                                    size_hint_y=None, height=dp(48))
        self.follow_input(self.date_input, scroll)
        form.add_widget(joined(label("Дата (ГГГГ-ММ-ДД)"), self.date_input))
        self.group_spinner = button("Выберите группу", lambda *_: self.choose_value(self.group_spinner, "Группа мышц"))
        self.group_spinner.values = tuple(EXERCISES)
        self.group_spinner.bind(text=self.on_group_changed)
        form.add_widget(joined(label("Группа мышц"), self.group_spinner))
        self.exercise_spinner = button("Выберите упражнение", lambda *_: self.choose_value(self.exercise_spinner, "Упражнение"))
        self.exercise_spinner.values = ()
        form.add_widget(joined(label("Упражнение"), self.exercise_spinner))
        form.add_widget(button("Открыть упражнение", self.open_exercise))
        self.current_label = label("Подходы: выберите дату и упражнение", 48)
        form.add_widget(self.current_label)
        headers = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        headers.add_widget(label("Повторы"))
        headers.add_widget(label("Вес, кг"))
        headers.add_widget(BoxLayout())
        self.sets_container = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        self.sets_container.bind(minimum_height=self.sets_container.setter("height"))
        form.add_widget(joined(headers, self.sets_container))
        form.add_widget(button("+ Добавить подход", self.add_set))
        form.add_widget(button("Сохранить упражнение", self.save_exercise))
        scroll.add_widget(form)
        self.entry_scroll = scroll
        self.replace_content(scroll)
        self.opened_key = None

    def show_entry(self):
        if not hasattr(self, "date_input"):
            self.build_entry()
        else:
            self.replace_content(self.entry_scroll)

    def on_group_changed(self, _spinner, group):
        self.exercise_spinner.values = EXERCISES.get(group, ())
        self.exercise_spinner.text = "Выберите упражнение"
        self.opened_key = None
        self.sets_container.clear_widgets()
        self.current_label.text = "Подходы: выберите упражнение"

    def open_exercise(self, *_):
        try:
            workout_date = parse_workout_date(self.date_input.text.strip()).isoformat()
            group = self.group_spinner.text
            exercise = self.exercise_spinner.text
            if group not in EXERCISES or exercise not in EXERCISES[group]:
                raise ValueError("Выберите группу мышц и упражнение")
            key = (workout_date, group, exercise)
            if self.opened_key != key:
                self.sets_container.clear_widgets()
                for reps, weight in self.store.get_sets(*key):
                    self.add_set(reps=reps, weight=weight)
                if not self.sets_container.children:
                    self.add_set()
            self.opened_key = key
            self.current_label.text = f"{exercise} — {workout_date}"
        except ValueError as error:
            self.show_message("Проверьте ввод", str(error))

    def add_set(self, *_args, reps: int | str = "", weight: float | str = ""):
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        reps_input = PixelTextInput(text=str(reps), hint_text="Повторы", input_filter="int",
                               multiline=False)
        weight_input = PixelTextInput(text=f"{weight:g}" if isinstance(weight, (int, float)) else weight,
                                 hint_text="Вес, кг", input_filter="float", multiline=False)
        self.follow_input(reps_input, self.entry_scroll)
        self.follow_input(weight_input, self.entry_scroll)
        row.add_widget(reps_input)
        row.add_widget(weight_input)
        row.add_widget(button("×", lambda *_: self.sets_container.remove_widget(row)))
        self.sets_container.add_widget(row)

    def save_exercise(self, *_):
        try:
            key = (self.date_input.text.strip(), self.group_spinner.text, self.exercise_spinner.text)
            if key != self.opened_key:
                raise ValueError("Сначала откройте упражнение для выбранной даты")
            sets = []
            for row in reversed(self.sets_container.children):
                reps_text = row.children[2].text.strip()
                weight_text = row.children[1].text.strip().replace(",", ".")
                if not reps_text or not weight_text:
                    raise ValueError("Заполните повторы и вес в каждом подходе")
                sets.append((int(reps_text), float(weight_text)))
            self.store.save_exercise(*key, sets)
            self.show_message("Сохранено", f"{key[2]}: {len(sets)} подход(а/ов)")
        except ValueError as error:
            self.show_message("Проверьте ввод", str(error))

    def show_history(self, *_):
        scroll = ScrollView()
        body = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        body.bind(minimum_height=body.setter("height"))
        body.add_widget(label("Сохранённые тренировки", 48))
        workouts = self.store.list_workouts()
        if not workouts:
            body.add_widget(label("Записей пока нет", 48))
        for workout_date, exercises, sets in workouts:
            body.add_widget(button(
                f"{workout_date}    {exercises} упр. / {sets} подх.",
                lambda _btn, day=workout_date: self.show_workout(day),
            ))
        body.add_widget(label("Очистка старых записей", 48))
        self.retention_input = PixelTextInput(text="365", input_filter="int", multiline=False,
                                         size_hint_y=None, height=dp(48))
        self.follow_input(self.retention_input, scroll)
        body.add_widget(joined(label("Удалить тренировки старше (дней):"), self.retention_input))
        body.add_widget(button("Очистить старые данные", self.confirm_cleanup))
        scroll.add_widget(body)
        self.replace_content(scroll)

    def show_workout(self, workout_date: str):
        details = self.store.workout_details(workout_date)
        body = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
        scroll = ScrollView()
        rows = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        rows.bind(minimum_height=rows.setter("height"))
        previous_exercise = None
        for group, exercise, position, reps, weight in details:
            if previous_exercise != (group, exercise):
                rows.add_widget(label(f"{group} · {exercise}", 42))
                previous_exercise = (group, exercise)
            rows.add_widget(label(f"  Подход {position}: {reps} × {weight:g} кг", 34))
        scroll.add_widget(rows)
        body.add_widget(scroll)
        body.add_widget(button("Закрыть", lambda *_: popup.dismiss()))
        popup = Popup(title=workout_date, content=body, size_hint=(0.95, 0.8))
        popup.open()

    def confirm_cleanup(self, *_):
        try:
            days = int(self.retention_input.text)
            count = self.store.count_older_than(days)
        except ValueError as error:
            self.show_message("Проверьте период", str(error))
            return
        if count == 0:
            self.show_message("Очистка", "Записей старше указанного периода нет")
            return
        body = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        body.add_widget(Label(text=f"Удалить {count} тренировок старше {days} дней?"))
        body.add_widget(button("Удалить", lambda *_: self.perform_cleanup(days, popup)))
        body.add_widget(button("Отмена", lambda *_: popup.dismiss()))
        popup = Popup(title="Подтвердите удаление", content=body, size_hint=(0.9, 0.5))
        popup.open()

    def perform_cleanup(self, days: int, popup: Popup):
        removed = self.store.delete_older_than(days)
        popup.dismiss()
        self.show_history()
        self.show_message("Очистка", f"Удалено тренировок: {removed}")


if __name__ == "__main__":
    WorkoutApp().run()
